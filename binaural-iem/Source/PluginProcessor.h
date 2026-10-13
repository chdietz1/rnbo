#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include "BinauralEngine.h"

class EarStageProcessor : public juce::AudioProcessor
{
public:
    EarStageProcessor();
    ~EarStageProcessor() override;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override {}
    bool isBusesLayoutSupported (const BusesLayout& layouts) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    using AudioProcessor::processBlock;
    void reset() override { engine.reset(); }

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return JucePlugin_Name; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    double getTailLengthSeconds() const override { return 1.5; }

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram (int) override {}
    const juce::String getProgramName (int) override { return {}; }
    void changeProgramName (int, const juce::String&) override {}

    void getStateInformation (juce::MemoryBlock& destData) override;
    void setStateInformation (const void* data, int sizeInBytes) override;

    void updateTrackProperties (const TrackProperties& properties) override;

    // Für die gemeinsame Bühnenansicht
    juce::String getDisplayName() const;
    juce::Colour getTrackColour() const;
    void setCustomName (const juce::String& name);
    juce::String getCustomName() const;
    int getInstanceNumber() const { return instanceNumber; }

    juce::AudioProcessorValueTreeState apvts;

    static constexpr const char* kAzimuth   = "azimuth";
    static constexpr const char* kElevation = "elevation";
    static constexpr const char* kDistance  = "distance";
    static constexpr const char* kWidth     = "width";
    static constexpr const char* kRoom      = "room";
    static constexpr const char* kRoomSize  = "roomSize";
    static constexpr const char* kHeadSize  = "headSize";
    static constexpr const char* kGain      = "gain";

private:
    static juce::AudioProcessorValueTreeState::ParameterLayout createLayout();

    earstage::Engine engine;
    std::atomic<float>* azimuth   = nullptr;
    std::atomic<float>* elevation = nullptr;
    std::atomic<float>* distance  = nullptr;
    std::atomic<float>* width     = nullptr;
    std::atomic<float>* room      = nullptr;
    std::atomic<float>* roomSize  = nullptr;
    std::atomic<float>* headSize  = nullptr;
    std::atomic<float>* gain      = nullptr;

    mutable juce::CriticalSection nameLock;
    juce::String trackName, customName;
    juce::Colour trackColour { juce::Colours::transparentBlack };
    int instanceNumber = 0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (EarStageProcessor)
};
