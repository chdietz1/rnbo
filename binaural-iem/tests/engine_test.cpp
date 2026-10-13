// Einfache Plausibilitätstests der binauralen Engine (ohne JUCE).
// Build: c++ -std=c++17 -O2 -I../Source engine_test.cpp -o engine_test && ./engine_test
#include "BinauralEngine.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

using namespace earstage;

static int failures = 0;
#define CHECK(cond, msg) do { if (! (cond)) { std::printf ("FAIL: %s\n", msg); ++failures; } else std::printf ("ok:   %s\n", msg); } while (0)

struct Result { double rmsL, rmsR; int lagSamples; bool finite; };

static Result render (Params p, bool stereo = false, double fs = 48000.0, int seconds = 1)
{
    Engine e;
    e.prepare (fs);
    e.setParams (p);
    const int n = (int) fs * seconds;
    std::vector<float> inL (n), inR (n), outL (n), outR (n);
    std::mt19937 rng (1);
    std::normal_distribution<float> nd (0.0f, 0.1f);
    for (int i = 0; i < n; ++i) { inL[i] = nd (rng); inR[i] = stereo ? nd (rng) : inL[i]; }

    for (int pos = 0; pos < n; pos += 256)
    {
        const int len = std::min (256, n - pos);
        e.process (inL.data() + pos, stereo ? inR.data() + pos : nullptr, outL.data() + pos, outR.data() + pos, len);
    }

    Result r { 0, 0, 0, true };
    const int skip = (int) (0.2 * fs);
    for (int i = skip; i < n; ++i)
    {
        r.rmsL += outL[i] * outL[i];
        r.rmsR += outR[i] * outR[i];
        if (! std::isfinite (outL[i]) || ! std::isfinite (outR[i])) r.finite = false;
    }
    r.rmsL = std::sqrt (r.rmsL / (n - skip));
    r.rmsR = std::sqrt (r.rmsR / (n - skip));

    // Kreuzkorrelation -> welches Ohr ist zuerst dran (positiv = rechts später)
    double best = -1e30;
    for (int lag = -48; lag <= 48; ++lag)
    {
        double acc = 0;
        for (int i = skip; i < n - 64; ++i)
            acc += (double) outL[i] * outR[i + lag];
        if (acc > best) { best = acc; r.lagSamples = lag; }
    }
    return r;
}

int main()
{
    Params p;
    p.roomAmount = 0.0f;

    p.azimuthDeg = 0;
    auto front = render (p);
    CHECK (front.finite, "Front: keine NaN/Inf");
    CHECK (std::abs (20 * std::log10 (front.rmsL / front.rmsR)) < 0.1, "Front: L/R gleich laut");
    CHECK (front.lagSamples == 0, "Front: keine ITD");
    std::printf ("      Front-Pegel: %.2f dB (Eingang -20 dB)\n", 20 * std::log10 (front.rmsL));

    p.azimuthDeg = 90;
    auto right = render (p);
    const double ildRight = 20 * std::log10 (right.rmsR / right.rmsL);
    std::printf ("      90° rechts: ILD %.1f dB, ITD %d Samples (%.2f ms)\n", ildRight, right.lagSamples, right.lagSamples / 48.0);
    CHECK (ildRight > 3.0, "90° rechts: rechts lauter");
    CHECK (right.lagSamples < -20 && right.lagSamples > -40, "90° rechts: linkes Ohr ~0.5-0.8 ms später");

    p.azimuthDeg = -90;
    auto left = render (p);
    CHECK (std::abs (20 * std::log10 (left.rmsL / left.rmsR) - ildRight) < 0.1, "Symmetrie links/rechts");
    CHECK (left.lagSamples == -right.lagSamples, "ITD-Symmetrie");

    p.azimuthDeg = 180;
    auto back = render (p);
    CHECK (back.rmsL < front.rmsL, "Hinten: Höhen gedämpft (leiser als vorne)");

    p.azimuthDeg = 0; p.distanceM = 6.0f;
    auto far = render (p);
    CHECK (far.rmsL < front.rmsL * 0.4, "Distanz: 6 m deutlich leiser als 1.5 m");
    p.distanceM = 1.5f;

    p.roomAmount = 1.0f; p.roomSize = 1.0f;
    auto room = render (p, false, 48000.0, 3);
    CHECK (room.finite, "Raum (max): stabil");
    CHECK (room.rmsL < 1.0, "Raum (max): kein Aufschwingen");

    p.widthDeg = 90; p.roomAmount = 0.25f;
    auto st = render (p, true, 44100.0);
    CHECK (st.finite && std::abs (20 * std::log10 (st.rmsL / st.rmsR)) < 1.0, "Stereoquelle mittig: ausgeglichen (44.1 kHz)");

    for (double fs : { 44100.0, 48000.0, 96000.0 })
    {
        Engine e; e.prepare (fs);
        std::vector<float> in (512, 0.1f), oL (512), oR (512);
        bool ok = true;
        for (int b = 0; b < 400; ++b)
        {
            Params q; q.azimuthDeg = (float) std::fmod (b * 37.0, 360.0) - 180.0f; q.elevationDeg = (float) (b % 130) - 40.0f;
            q.distanceM = 0.5f + (b % 15); q.roomAmount = 1.0f; q.roomSize = (b % 10) / 10.0f;
            e.setParams (q);
            e.process (in.data(), nullptr, oL.data(), oR.data(), 512);
            for (int i = 0; i < 512; ++i) ok = ok && std::isfinite (oL[i]) && std::abs (oL[i]) < 10.0f;
        }
        char msg[64]; std::snprintf (msg, sizeof msg, "Automationsstress @ %.0f Hz stabil", fs);
        CHECK (ok, msg);
    }

    std::printf ("\n%s (%d Fehler)\n", failures == 0 ? "ALLE TESTS OK" : "TESTS FEHLGESCHLAGEN", failures);
    return failures == 0 ? 0 : 1;
}
