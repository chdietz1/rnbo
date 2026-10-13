// EarStage – binaurale Engine (ohne JUCE-Abhängigkeit, damit sie separat testbar ist)
//
// Modell pro virtueller Quelle (strukturelles HRTF-Modell nach Brown & Duda 1998):
//   Eingang -> Luftdämpfung (Distanz) -> Ohrmuschel/Front-Hinten-Cues -> Verzögerungsleitung
//           -> je Ohr: ITD (Woodworth, fraktionale Verzögerung) -> Kopfschatten-Filter
// Dazu ein kleiner Raum (Early Reflections + 4er-FDN) für die Externalisierung,
// damit der Mix "vor" dem Kopf und nicht "im" Kopf stattfindet.
//
// Konvention: Azimut 0° = vorne, +90° = rechts, ±180° = hinten. Elevation +90° = oben.
#pragma once

#include <algorithm>
#include <cmath>
#include <vector>

namespace earstage
{

constexpr float kPi = 3.14159265358979323846f;
constexpr float kSpeedOfSound = 343.0f;

inline float degToRad (float d) { return d * (kPi / 180.0f); }
inline float dbToGain (float db) { return std::pow (10.0f, db / 20.0f); }

inline float wrapDegrees (float d)
{
    while (d > 180.0f) d -= 360.0f;
    while (d < -180.0f) d += 360.0f;
    return d;
}

//==============================================================================
struct Biquad
{
    float b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
    float z1 = 0, z2 = 0;

    float process (float x)
    {
        const float y = b0 * x + z1;
        z1 = b1 * x - a1 * y + z2;
        z2 = b2 * x - a2 * y;
        return y;
    }

    void reset() { z1 = z2 = 0; }

    // RBJ Peaking-EQ
    void setPeak (float fs, float f, float q, float gainDb)
    {
        f = std::min (f, 0.45f * fs);
        const float A = std::pow (10.0f, gainDb / 40.0f);
        const float w = 2.0f * kPi * f / fs;
        const float alpha = std::sin (w) / (2.0f * q);
        const float c = std::cos (w);
        const float a0 = 1.0f + alpha / A;
        b0 = (1.0f + alpha * A) / a0;
        b1 = (-2.0f * c) / a0;
        b2 = (1.0f - alpha * A) / a0;
        a1 = (-2.0f * c) / a0;
        a2 = (1.0f - alpha / A) / a0;
    }

    // RBJ High-Shelf (S = 1)
    void setHighShelf (float fs, float f, float gainDb)
    {
        f = std::min (f, 0.45f * fs);
        const float A = std::pow (10.0f, gainDb / 40.0f);
        const float w = 2.0f * kPi * f / fs;
        const float c = std::cos (w);
        const float alpha = std::sin (w) / 2.0f * std::sqrt (2.0f);
        const float sA = 2.0f * std::sqrt (A) * alpha;
        const float a0 = (A + 1) - (A - 1) * c + sA;
        b0 = A * ((A + 1) + (A - 1) * c + sA) / a0;
        b1 = -2 * A * ((A - 1) + (A + 1) * c) / a0;
        b2 = A * ((A + 1) + (A - 1) * c - sA) / a0;
        a1 = 2 * ((A - 1) - (A + 1) * c) / a0;
        a2 = ((A + 1) - (A - 1) * c - sA) / a0;
    }
};

//==============================================================================
struct OnePoleLowpass
{
    float a = 0, y = 0;

    void setCutoff (float fs, float f)
    {
        f = std::min (f, 0.45f * fs);
        a = std::exp (-2.0f * kPi * f / fs);
    }

    float process (float x) { y = x + a * (y - x); return y; }
    void reset() { y = 0; }
};

//==============================================================================
// Kopfschatten nach Brown & Duda: H(s) = (1 + alpha*tau*s) / (1 + tau*s), tau = a / (2c)
struct HeadShadow
{
    float b0 = 1, b1 = 0, a1 = 0, x1 = 0, y1 = 0;

    void set (float fs, float headRadius, float alpha)
    {
        const float wc = 2.0f * kSpeedOfSound / headRadius;               // 2*omega0
        const float tau = 1.0f / wc;
        const float K = wc / std::tan (std::min (wc / (2.0f * fs), 1.5f)); // Prewarping auf die Eckfrequenz
        const float a0 = 1.0f + tau * K;
        b0 = (1.0f + alpha * tau * K) / a0;
        b1 = (1.0f - alpha * tau * K) / a0;
        a1 = (1.0f - tau * K) / a0;
    }

    float process (float x)
    {
        const float y = b0 * x + b1 * x1 - a1 * y1;
        x1 = x;
        y1 = y;
        return y;
    }

    void reset() { x1 = y1 = 0; }
};

//==============================================================================
class DelayLine
{
public:
    void prepare (int maxDelaySamples)
    {
        int size = 1;
        while (size < maxDelaySamples + 8) size <<= 1;
        buffer.assign ((size_t) size, 0.0f);
        mask = size - 1;
        writePos = 0;
    }

    void reset() { std::fill (buffer.begin(), buffer.end(), 0.0f); }

    void push (float x)
    {
        writePos = (writePos + 1) & mask;
        buffer[(size_t) writePos] = x;
    }

    // Verzögerung in Samples (>= 0), 4-Punkt-Hermite-Interpolation.
    // read(0) liefert das zuletzt geschriebene Sample.
    float read (float delay) const
    {
        delay = std::max (delay, 1.0f); // ein Sample Reserve für den Interpolator
        const int   i = (int) delay;
        const float f = delay - (float) i;
        const float xm1 = at (i - 1), x0 = at (i), x1 = at (i + 1), x2 = at (i + 2);
        const float c1 = 0.5f * (x1 - xm1);
        const float c2 = xm1 - 2.5f * x0 + 2.0f * x1 - 0.5f * x2;
        const float c3 = 0.5f * (x2 - xm1) + 1.5f * (x0 - x1);
        return ((c3 * f + c2) * f + c1) * f + x0;
    }

private:
    float at (int d) const { return buffer[(size_t) ((writePos - d) & mask)]; }

    std::vector<float> buffer;
    int mask = 0, writePos = 0;
};

//==============================================================================
struct Direction
{
    float azimuthDeg = 0, elevationDeg = 0;
};

// Eine binaural gerenderte Punktquelle
class PointSource
{
public:
    void prepare (float sampleRate)
    {
        fs = sampleRate;
        delay.prepare ((int) std::ceil (0.002f * fs) + 4); // max. ITD ~0.8 ms bei 10 cm Kopf
        reset();
    }

    void reset()
    {
        delay.reset();
        shadowL.reset(); shadowR.reset();
        backShelf.reset(); pinnaNotch.reset(); concha.reset();
        air.reset();
        first = true;
    }

    // einmal pro Sub-Block aufrufen
    void update (Direction dir, float distanceM, float headRadiusM)
    {
        const float az = degToRad (dir.azimuthDeg);
        const float el = degToRad (dir.elevationDeg);
        // Einheitsvektor: x = rechts, y = vorne, z = oben
        const float x = std::sin (az) * std::cos (el);
        const float y = std::cos (az) * std::cos (el);

        // Winkel zwischen Quelle und Ohrachse (0 = direkt auf das Ohr)
        const float thetaR = std::acos (std::clamp (x, -1.0f, 1.0f));
        const float thetaL = std::acos (std::clamp (-x, -1.0f, 1.0f));

        // ITD nach Woodworth, mit konstantem Offset a/c, damit nichts negativ wird
        const float aOverC = headRadiusM / kSpeedOfSound;
        auto earDelay = [&] (float theta)
        {
            const float t = theta < 0.5f * kPi ? -std::cos (theta) : (theta - 0.5f * kPi);
            return aOverC * (1.0f + t) * fs;
        };
        targetDelayL = earDelay (thetaL);
        targetDelayR = earDelay (thetaR);

        // Kopfschatten, normalisiert, so dass eine Quelle von vorne linear klingt
        auto alphaFor = [] (float thetaRad)
        {
            constexpr float alphaMin = 0.1f, thetaMin = 150.0f;
            const float thetaDeg = thetaRad * (180.0f / kPi);
            return (1.0f + alphaMin / 2.0f) + (1.0f - alphaMin / 2.0f) * std::cos (degToRad (thetaDeg / thetaMin * 180.0f));
        };
        const float alphaFront = alphaFor (0.5f * kPi);
        shadowL.set (fs, headRadiusM, std::clamp (alphaFor (thetaL) / alphaFront, 0.08f, 2.0f));
        shadowR.set (fs, headRadiusM, std::clamp (alphaFor (thetaR) / alphaFront, 0.08f, 2.0f));

        // Vorne/Hinten: die Ohrmuschel schattet Höhen von hinten ab, vorne leichte Concha-Resonanz
        const float back = std::max (0.0f, -y);
        const float front = std::max (0.0f, y);
        backShelf.setHighShelf (fs, 4500.0f, -7.0f * back);
        concha.setPeak (fs, 3200.0f, 1.2f, 2.0f * front);

        // Elevation: die Pinna-Kerbe wandert mit steigender Elevation nach oben und wird flacher
        const float elNorm = dir.elevationDeg / 90.0f;
        const float notchF = 7000.0f + 4500.0f * elNorm;
        const float notchDepth = -10.0f * (1.0f - 0.7f * std::max (0.0f, elNorm));
        pinnaNotch.setPeak (fs, std::max (notchF, 3000.0f), 2.5f, notchDepth);

        // Luftdämpfung
        air.setCutoff (fs, 20000.0f / (1.0f + 0.12f * distanceM));

        if (first)
        {
            delayL = targetDelayL;
            delayR = targetDelayR;
            first = false;
        }
    }

    void process (float in, float& outL, float& outR)
    {
        float s = air.process (in);
        s = concha.process (backShelf.process (pinnaNotch.process (s)));
        delay.push (s);

        // pro Sample geglättete Verzögerung -> keine Zipper-Geräusche beim Bewegen
        delayL += delaySmooth * (targetDelayL - delayL);
        delayR += delaySmooth * (targetDelayR - delayR);

        outL += shadowL.process (delay.read (delayL));
        outR += shadowR.process (delay.read (delayR));
    }

    void setDelaySmoothing (float coeff) { delaySmooth = coeff; }

private:
    float fs = 48000.0f;
    DelayLine delay;
    HeadShadow shadowL, shadowR;
    Biquad backShelf, pinnaNotch, concha;
    OnePoleLowpass air;
    float targetDelayL = 0, targetDelayR = 0, delayL = 0, delayR = 0;
    float delaySmooth = 0.002f;
    bool first = true;
};

//==============================================================================
// Kleiner Raum: frühe Reflexionen + 4-Kanal-FDN (Hadamard), kurze Nachhallzeit
class Room
{
public:
    void prepare (float sampleRate)
    {
        fs = sampleRate;
        const int maxSamples = (int) std::ceil (0.15f * fs);
        er.prepare (maxSamples);
        for (auto& l : lines) l.prepare (maxSamples);
        reset();
    }

    void reset()
    {
        er.reset();
        for (auto& l : lines) l.reset();
        for (auto& d : damping) d.reset();
    }

    // size: 0..1
    void update (float size)
    {
        targetScale = 0.5f + 1.5f * size;
        const float rt60 = 0.2f + 0.9f * size;
        for (int i = 0; i < 4; ++i)
        {
            const float lenSeconds = kLineMs[i] * 0.001f * targetScale;
            gains[i] = std::pow (10.0f, -3.0f * lenSeconds / rt60);
            damping[i].setCutoff (fs, 9000.0f - 4000.0f * size);
        }
    }

    void process (float in, float& outL, float& outR)
    {
        scale += 0.0005f * (targetScale - scale);

        er.push (in);
        float erL = 0, erR = 0;
        for (int i = 0; i < kNumTaps; ++i)
        {
            erL += kTapGain[i] * er.read (kTapMsL[i] * 0.001f * fs * scale);
            erR += kTapGain[i] * er.read (kTapMsR[i] * 0.001f * fs * scale);
        }

        float d[4];
        for (int i = 0; i < 4; ++i)
            d[i] = lines[i].read (kLineMs[i] * 0.001f * fs * scale);

        // Hadamard-Feedback-Matrix (orthogonal, verlustfrei)
        const float h0 = 0.5f * (d[0] + d[1] + d[2] + d[3]);
        const float h1 = 0.5f * (d[0] - d[1] + d[2] - d[3]);
        const float h2 = 0.5f * (d[0] + d[1] - d[2] - d[3]);
        const float h3 = 0.5f * (d[0] - d[1] - d[2] + d[3]);
        const float fb[4] = { h0, h1, h2, h3 };
        const float input = 0.35f * (erL + erR);

        for (int i = 0; i < 4; ++i)
            lines[i].push (input + gains[i] * damping[i].process (fb[i]));

        outL += erL + 0.5f * (d[0] - d[1] + d[2] - d[3]);
        outR += erR + 0.5f * (d[0] + d[1] - d[2] - d[3]);
    }

private:
    static constexpr int kNumTaps = 6;
    static constexpr float kTapMsL[kNumTaps]  = { 4.3f, 9.7f, 14.2f, 21.5f, 29.8f, 37.3f };
    static constexpr float kTapMsR[kNumTaps]  = { 5.1f, 8.6f, 16.3f, 19.9f, 27.4f, 39.1f };
    static constexpr float kTapGain[kNumTaps] = { 0.45f, 0.38f, 0.30f, 0.24f, 0.19f, 0.15f };
    static constexpr float kLineMs[4] = { 29.7f, 37.1f, 41.1f, 43.7f };

    float fs = 48000.0f;
    DelayLine er;
    DelayLine lines[4];
    OnePoleLowpass damping[4];
    float gains[4] { 0, 0, 0, 0 };
    float scale = 1.0f, targetScale = 1.0f;
};

//==============================================================================
struct Params
{
    float azimuthDeg   = 0.0f;   // -180..180
    float elevationDeg = 0.0f;   // -40..90
    float distanceM    = 1.5f;   // 0.5..15
    float widthDeg     = 30.0f;  // Stereobreite bei Stereoquellen
    float roomAmount   = 0.25f;  // 0..1
    float roomSize     = 0.4f;   // 0..1
    float headRadiusM  = 0.0875f;
    float gainDb       = 0.0f;
};

class Engine
{
public:
    static constexpr float kReferenceDistance = 1.5f;

    void prepare (double sampleRate)
    {
        fs = (float) sampleRate;
        for (auto& s : sources)
        {
            s.prepare (fs);
            s.setDelaySmoothing (1.0f - std::exp (-1.0f / (0.015f * fs)));
        }
        room.prepare (fs);
        perSample = 1.0f - std::exp (-1.0f / (0.02f * fs));
        perBlock  = 1.0f - std::exp (-(float) kSubBlock / (0.03f * fs));
        firstBlock = true;
    }

    void reset()
    {
        for (auto& s : sources) s.reset();
        room.reset();
        firstBlock = true;
    }

    void setParams (const Params& p) { target = p; }

    // inR darf nullptr sein (Mono-Quelle). Ausgänge werden überschrieben.
    void process (const float* inL, const float* inR, float* outL, float* outR, int numSamples)
    {
        if (firstBlock)
        {
            current = target;
            gainLin = distanceGain (current.distanceM) * dbToGain (current.gainDb);
            roomLin = current.roomAmount;
            firstBlock = false;
        }

        for (int start = 0; start < numSamples; start += kSubBlock)
        {
            const int n = std::min (kSubBlock, numSamples - start);
            smoothParams();

            const bool stereo = inR != nullptr && current.widthDeg > 0.5f;
            const float halfWidth = stereo ? 0.5f * current.widthDeg : 0.0f;
            sources[0].update ({ wrapDegrees (current.azimuthDeg - halfWidth), current.elevationDeg }, current.distanceM, current.headRadiusM);
            if (stereo)
                sources[1].update ({ wrapDegrees (current.azimuthDeg + halfWidth), current.elevationDeg }, current.distanceM, current.headRadiusM);
            room.update (current.roomSize);

            const float gainTarget = distanceGain (current.distanceM) * dbToGain (current.gainDb);
            const float roomTarget = current.roomAmount;
            const float userGain = dbToGain (current.gainDb);

            for (int i = start; i < start + n; ++i)
            {
                gainLin += perSample * (gainTarget - gainLin);
                roomLin += perSample * (roomTarget - roomLin);

                const float l = inL[i];
                const float r = inR != nullptr ? inR[i] : l;
                float yl = 0, yr = 0;

                if (stereo)
                {
                    // -3 dB, damit korrelierte Stereo-Signale nicht lauter werden als mono
                    sources[0].process (0.7071f * l * gainLin, yl, yr);
                    sources[1].process (0.7071f * r * gainLin, yl, yr);
                }
                else
                {
                    sources[0].process (0.5f * (l + r) * gainLin, yl, yr);
                }

                // Raum bekommt einen distanzunabhängigen Pegel -> ferne Quellen klingen halliger
                float wl = 0, wr = 0;
                room.process (0.5f * (l + r) * userGain, wl, wr);

                outL[i] = yl + roomLin * 0.6f * wl;
                outR[i] = yr + roomLin * 0.6f * wr;
            }
        }
    }

private:
    static constexpr int kSubBlock = 16;

    static float distanceGain (float d) { return kReferenceDistance / std::max (d, 0.5f); }

    void smoothParams()
    {
        // Azimut auf dem kürzesten Weg glätten (179° -> -179° geht nicht einmal rundherum)
        current.azimuthDeg = wrapDegrees (current.azimuthDeg + perBlock * wrapDegrees (target.azimuthDeg - current.azimuthDeg));
        current.elevationDeg += perBlock * (target.elevationDeg - current.elevationDeg);
        current.distanceM    += perBlock * (target.distanceM - current.distanceM);
        current.widthDeg     += perBlock * (target.widthDeg - current.widthDeg);
        current.roomSize     += perBlock * (target.roomSize - current.roomSize);
        current.headRadiusM  += perBlock * (target.headRadiusM - current.headRadiusM);
        current.gainDb       += perBlock * (target.gainDb - current.gainDb);
        current.roomAmount = target.roomAmount; // wird pro Sample geglättet
    }

    float fs = 48000.0f;
    PointSource sources[2];
    Room room;
    Params target, current;
    float perSample = 0.001f, perBlock = 0.01f;
    float gainLin = 1.0f, roomLin = 0.0f;
    bool firstBlock = true;
};

} // namespace earstage
