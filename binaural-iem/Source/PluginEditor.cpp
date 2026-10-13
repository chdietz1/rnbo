#include "PluginEditor.h"
#include "StageRegistry.h"

namespace
{
const juce::Colour kBackground { 0xff15171c };
const juce::Colour kPanel      { 0xff1e2128 };
const juce::Colour kGrid       { 0xff343844 };
const juce::Colour kText       { 0xffd9dce3 };
const juce::Colour kAccent     { 0xff4fc3f7 };

constexpr float kMinDistance = 0.5f;
constexpr float kMaxDistance = 15.0f;

// Distanz -> Radius 0..1 (logarithmisch, damit der Nahbereich genug Platz bekommt)
float distanceToRadius (float d)
{
    return std::log (d / kMinDistance + 1.0f) / std::log (kMaxDistance / kMinDistance + 1.0f);
}

float radiusToDistance (float r)
{
    return kMinDistance * (std::exp (r * std::log (kMaxDistance / kMinDistance + 1.0f)) - 1.0f);
}

juce::Colour colourFor (EarStageProcessor* p)
{
    auto c = p->getTrackColour();
    if (c.getAlpha() > 0)
        return c;
    return juce::Colour::fromHSV (std::fmod (p->getInstanceNumber() * 0.137f, 1.0f), 0.55f, 0.95f, 1.0f);
}
} // namespace

//==============================================================================
StageView::StageView (EarStageProcessor& o) : owner (o)
{
    startTimerHz (30);
}

juce::Point<float> StageView::toScreen (float azimuthDeg, float distanceM) const
{
    const auto c = getLocalBounds().toFloat().getCentre();
    const float R = 0.46f * (float) juce::jmin (getWidth(), getHeight());
    const float r = R * distanceToRadius (distanceM);
    const float a = juce::degreesToRadians (azimuthDeg);
    return { c.x + r * std::sin (a), c.y - r * std::cos (a) };
}

StageView::Polar StageView::fromScreen (juce::Point<float> p) const
{
    const auto c = getLocalBounds().toFloat().getCentre();
    const float R = 0.46f * (float) juce::jmin (getWidth(), getHeight());
    const auto d = p - c;
    const float az = juce::radiansToDegrees (std::atan2 (d.x, -d.y));
    const float r = juce::jlimit (0.0f, 1.0f, d.getDistanceFromOrigin() / R);
    return { az, juce::jlimit (kMinDistance, kMaxDistance, radiusToDistance (r)) };
}

void StageView::paint (juce::Graphics& g)
{
    const auto bounds = getLocalBounds().toFloat();
    const auto c = bounds.getCentre();
    const float R = 0.46f * juce::jmin (bounds.getWidth(), bounds.getHeight());

    g.setColour (kPanel);
    g.fillEllipse (juce::Rectangle<float> (2 * R, 2 * R).withCentre (c));

    // Distanzringe
    g.setFont (11.0f);
    for (float d : { 1.0f, 2.0f, 4.0f, 8.0f })
    {
        const float r = R * distanceToRadius (d);
        g.setColour (kGrid);
        g.drawEllipse (juce::Rectangle<float> (2 * r, 2 * r).withCentre (c), 1.0f);
        g.setColour (kGrid.brighter (0.6f));
        g.drawText (juce::String ((int) d) + " m", juce::Rectangle<float> (40, 14).withPosition (c.x + r * 0.7071f + 3, c.y + r * 0.7071f - 2),
                    juce::Justification::centredLeft);
    }

    // Achsen + Beschriftung
    g.setColour (kGrid);
    for (int a = 0; a < 360; a += 45)
    {
        const float rad = juce::degreesToRadians ((float) a);
        g.drawLine (c.x + 0.12f * R * std::sin (rad), c.y - 0.12f * R * std::cos (rad),
                    c.x + R * std::sin (rad), c.y - R * std::cos (rad), 0.6f);
    }
    g.setColour (kText.withAlpha (0.6f));
    g.drawText ("VORNE", juce::Rectangle<float> (80, 16).withCentre ({ c.x, c.y - R - 10 }), juce::Justification::centred);
    g.drawText ("HINTEN", juce::Rectangle<float> (80, 16).withCentre ({ c.x, c.y + R + 10 }), juce::Justification::centred);
    g.drawText ("L", juce::Rectangle<float> (20, 16).withCentre ({ c.x - R - 10, c.y }), juce::Justification::centred);
    g.drawText ("R", juce::Rectangle<float> (20, 16).withCentre ({ c.x + R + 10, c.y }), juce::Justification::centred);

    // Kopf
    const float head = 0.07f * R;
    g.setColour (kText.withAlpha (0.85f));
    g.fillEllipse (juce::Rectangle<float> (2 * head, 2.2f * head).withCentre (c));
    juce::Path nose;
    nose.addTriangle (c.x - head * 0.35f, c.y - head * 0.95f, c.x + head * 0.35f, c.y - head * 0.95f, c.x, c.y - head * 1.5f);
    g.fillPath (nose);
    g.fillEllipse (juce::Rectangle<float> (head * 0.5f, head * 0.8f).withCentre ({ c.x - head, c.y }));
    g.fillEllipse (juce::Rectangle<float> (head * 0.5f, head * 0.8f).withCentre ({ c.x + head, c.y }));

    // Quellen: zuerst die anderen, dann die eigene obendrauf
    auto instances = StageRegistry::get().snapshot();
    std::stable_partition (instances.begin(), instances.end(), [this] (auto* p) { return p != &owner; });

    for (auto* p : instances)
    {
        const bool mine = p == &owner;
        const float az   = p->apvts.getRawParameterValue (EarStageProcessor::kAzimuth)->load();
        const float dist = p->apvts.getRawParameterValue (EarStageProcessor::kDistance)->load();
        const float el   = p->apvts.getRawParameterValue (EarStageProcessor::kElevation)->load();
        const float wid  = p->apvts.getRawParameterValue (EarStageProcessor::kWidth)->load();
        const auto pos = toScreen (az, dist);
        const auto col = colourFor (p);

        // Stereobreite als Bogen
        if (p->getTotalNumInputChannels() > 1 && wid > 0.5f)
        {
            const float r = pos.getDistanceFrom (c);
            juce::Path arc;
            arc.addCentredArc (c.x, c.y, r, r, 0.0f, juce::degreesToRadians (az - wid * 0.5f),
                               juce::degreesToRadians (az + wid * 0.5f), true);
            g.setColour (col.withAlpha (mine ? 0.7f : 0.35f));
            g.strokePath (arc, juce::PathStrokeType (mine ? 4.0f : 2.5f, juce::PathStrokeType::curved, juce::PathStrokeType::rounded));
        }

        // Elevation: größerer Punkt = höher
        const float size = (mine ? 16.0f : 12.0f) * (1.0f + 0.5f * el / 90.0f);
        g.setColour (col.withAlpha (mine ? 1.0f : 0.75f));
        g.fillEllipse (juce::Rectangle<float> (size, size).withCentre (pos));
        if (mine)
        {
            g.setColour (juce::Colours::white);
            g.drawEllipse (juce::Rectangle<float> (size + 6, size + 6).withCentre (pos), 2.0f);
        }

        g.setColour (mine ? juce::Colours::white : kText.withAlpha (0.8f));
        g.setFont (mine ? 13.0f : 11.5f);
        auto text = p->getDisplayName();
        if (std::abs (el) >= 1.0f)
            text << "  " << (el > 0 ? "+" : "") << juce::roundToInt (el) << juce::String::fromUTF8 ("\xc2\xb0");
        g.drawText (text, juce::Rectangle<float> (160, 16).withPosition (pos.x + size * 0.5f + 4, pos.y - 8),
                    juce::Justification::centredLeft);
    }
}

EarStageProcessor* StageView::findSourceAt (juce::Point<float> pt) const
{
    EarStageProcessor* best = nullptr;
    float bestDist = 18.0f;
    for (auto* p : StageRegistry::get().snapshot())
    {
        const auto pos = toScreen (p->apvts.getRawParameterValue (EarStageProcessor::kAzimuth)->load(),
                                   p->apvts.getRawParameterValue (EarStageProcessor::kDistance)->load());
        float d = pos.getDistanceFrom (pt);
        if (p == &owner) d -= 4.0f; // eigene Quelle bevorzugen
        if (d < bestDist) { bestDist = d; best = p; }
    }
    return best;
}

void StageView::setParam (EarStageProcessor* p, const char* id, float value)
{
    if (auto* param = p->apvts.getParameter (id))
        param->setValueNotifyingHost (param->convertTo0to1 (value));
}

void StageView::mouseDown (const juce::MouseEvent& e)
{
    // Klick auf eine Quelle -> diese ziehen; Klick ins Leere -> eigene Quelle dorthin setzen
    dragging = findSourceAt (e.position);
    if (dragging == nullptr && ! e.mods.isPopupMenu())
        dragging = &owner;

    if (dragging != nullptr)
    {
        dragging->apvts.getParameter (EarStageProcessor::kAzimuth)->beginChangeGesture();
        dragging->apvts.getParameter (EarStageProcessor::kDistance)->beginChangeGesture();
        mouseDrag (e);
    }
}

void StageView::mouseDrag (const juce::MouseEvent& e)
{
    if (dragging == nullptr || ! StageRegistry::get().contains (dragging))
        return;

    auto polar = fromScreen (e.position);
    if (e.mods.isShiftDown()) // Shift: nur Winkel ändern, Distanz bleibt
        polar.distance = dragging->apvts.getRawParameterValue (EarStageProcessor::kDistance)->load();
    if (e.mods.isAltDown())   // Alt: auf 15°-Raster einrasten
        polar.azimuth = 15.0f * std::round (polar.azimuth / 15.0f);

    setParam (dragging, EarStageProcessor::kAzimuth, polar.azimuth);
    setParam (dragging, EarStageProcessor::kDistance, polar.distance);
}

void StageView::mouseUp (const juce::MouseEvent&)
{
    if (dragging != nullptr && StageRegistry::get().contains (dragging))
    {
        dragging->apvts.getParameter (EarStageProcessor::kAzimuth)->endChangeGesture();
        dragging->apvts.getParameter (EarStageProcessor::kDistance)->endChangeGesture();
    }
    dragging = nullptr;
}

void StageView::mouseWheelMove (const juce::MouseEvent& e, const juce::MouseWheelDetails& w)
{
    // Mausrad über einer Quelle: Elevation
    auto* target = findSourceAt (e.position);
    if (target == nullptr)
        target = &owner;
    const float el = target->apvts.getRawParameterValue (EarStageProcessor::kElevation)->load();
    setParam (target, EarStageProcessor::kElevation, juce::jlimit (-40.0f, 90.0f, el + w.deltaY * 30.0f));
}

//==============================================================================
EarStageEditor::EarStageEditor (EarStageProcessor& p)
    : AudioProcessorEditor (&p), processor (p), stage (p)
{
    lnf.setColour (juce::Slider::rotarySliderFillColourId, kAccent);
    lnf.setColour (juce::Slider::rotarySliderOutlineColourId, kGrid);
    lnf.setColour (juce::Slider::thumbColourId, juce::Colours::white);
    lnf.setColour (juce::Slider::textBoxOutlineColourId, juce::Colours::transparentBlack);
    lnf.setColour (juce::Slider::textBoxTextColourId, kText);
    lnf.setColour (juce::Label::textColourId, kText);
    setLookAndFeel (&lnf);

    addAndMakeVisible (stage);

    nameLabel.setText ("Quelle:", juce::dontSendNotification);
    addAndMakeVisible (nameLabel);

    nameEditor.setEditable (true);
    nameEditor.setText (p.getCustomName(), juce::dontSendNotification);
    nameEditor.setColour (juce::Label::backgroundColourId, kPanel);
    nameEditor.setColour (juce::Label::outlineColourId, kGrid);
    nameEditor.setTooltip ("Leer lassen = Spurname aus Ableton");
    nameEditor.onTextChange = [this] { processor.setCustomName (nameEditor.getText()); };
    addAndMakeVisible (nameEditor);

    hint.setText (juce::String::fromUTF8 ("Ziehen: Quelle bewegen \xc2\xb7 Shift: nur Winkel \xc2\xb7 Alt: 15\xc2\xb0-Raster \xc2\xb7 Mausrad: H\xc3\xb6he"),
                  juce::dontSendNotification);
    hint.setFont (juce::FontOptions (11.5f));
    hint.setColour (juce::Label::textColourId, kText.withAlpha (0.55f));
    addAndMakeVisible (hint);

    addKnob (azimuth,   EarStageProcessor::kAzimuth,   "Azimut");
    addKnob (elevation, EarStageProcessor::kElevation, juce::String::fromUTF8 ("H\xc3\xb6he"));
    addKnob (distance,  EarStageProcessor::kDistance,  "Distanz");
    addKnob (width,     EarStageProcessor::kWidth,     "Stereobreite");
    addKnob (room,      EarStageProcessor::kRoom,      "Raum");
    addKnob (roomSize,  EarStageProcessor::kRoomSize,  juce::String::fromUTF8 ("Raumgr\xc3\xb6\xc3\x9f" "e"));
    addKnob (gain,      EarStageProcessor::kGain,      "Gain");
    addKnob (headSize,  EarStageProcessor::kHeadSize,  "Kopfradius");

    setResizable (true, true);
    setResizeLimits (640, 460, 1400, 1000);
    setSize (780, 540);
}

EarStageEditor::~EarStageEditor()
{
    setLookAndFeel (nullptr);
}

void EarStageEditor::addKnob (Knob& k, const char* paramId, const juce::String& title)
{
    k.slider.setTextBoxStyle (juce::Slider::TextBoxBelow, false, 70, 18);
    addAndMakeVisible (k.slider);
    k.label.setText (title, juce::dontSendNotification);
    k.label.setJustificationType (juce::Justification::centred);
    addAndMakeVisible (k.label);
    k.attachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment> (processor.apvts, paramId, k.slider);
}

void EarStageEditor::paint (juce::Graphics& g)
{
    g.fillAll (kBackground);
    g.setColour (kText);
    g.setFont (juce::FontOptions (20.0f, juce::Font::bold));
    g.drawText ("EarStage", 16, 10, 200, 26, juce::Justification::centredLeft);
    g.setFont (juce::FontOptions (12.0f));
    g.setColour (kText.withAlpha (0.55f));
    g.drawText ("binaurales In-Ear-Monitoring", 112, 14, 260, 20, juce::Justification::centredLeft);
}

void EarStageEditor::resized()
{
    auto area = getLocalBounds().reduced (12);
    area.removeFromTop (34);

    auto right = area.removeFromRight (240);
    hint.setBounds (area.removeFromBottom (20));
    stage.setBounds (area.reduced (4));

    auto nameRow = right.removeFromTop (28);
    nameLabel.setBounds (nameRow.removeFromLeft (56));
    nameEditor.setBounds (nameRow.reduced (0, 2));
    right.removeFromTop (8);

    Knob* knobs[] = { &azimuth, &elevation, &distance, &width, &room, &roomSize, &gain, &headSize };
    const int rows = 4;
    const int rowH = right.getHeight() / rows;
    for (int i = 0; i < 8; ++i)
    {
        auto cell = juce::Rectangle<int> (right.getX() + (i % 2) * right.getWidth() / 2, right.getY() + (i / 2) * rowH,
                                          right.getWidth() / 2, rowH);
        knobs[i]->label.setBounds (cell.removeFromTop (18));
        knobs[i]->slider.setBounds (cell.reduced (6, 0).withTrimmedBottom (8));
    }
}
