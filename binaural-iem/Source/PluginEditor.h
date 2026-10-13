#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "PluginProcessor.h"

// Draufsicht: Kopf in der Mitte, Nase zeigt nach oben. Zeigt ALLE EarStage-Instanzen.
class StageView : public juce::Component, private juce::Timer
{
public:
    explicit StageView (EarStageProcessor& owner);

    void paint (juce::Graphics&) override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseDrag (const juce::MouseEvent&) override;
    void mouseUp (const juce::MouseEvent&) override;
    void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails&) override;

private:
    void timerCallback() override { repaint(); }

    struct Polar { float azimuth, distance; };
    juce::Point<float> toScreen (float azimuthDeg, float distanceM) const;
    Polar fromScreen (juce::Point<float>) const;
    EarStageProcessor* findSourceAt (juce::Point<float>) const;
    void setParam (EarStageProcessor*, const char* id, float value);

    EarStageProcessor& owner;
    EarStageProcessor* dragging = nullptr;
};

class EarStageEditor : public juce::AudioProcessorEditor
{
public:
    explicit EarStageEditor (EarStageProcessor&);
    ~EarStageEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

private:
    struct Knob
    {
        juce::Slider slider { juce::Slider::RotaryHorizontalVerticalDrag, juce::Slider::TextBoxBelow };
        juce::Label label;
        std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> attachment;
    };

    void addKnob (Knob&, const char* paramId, const juce::String& title);

    EarStageProcessor& processor;
    juce::LookAndFeel_V4 lnf;
    StageView stage;
    juce::Label nameLabel, nameEditor, hint;
    Knob azimuth, elevation, distance, width, room, roomSize, gain, headSize;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (EarStageEditor)
};
