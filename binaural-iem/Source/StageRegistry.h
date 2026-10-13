#pragma once

#include <algorithm>
#include <mutex>
#include <vector>

class EarStageProcessor;

// Alle EarStage-Instanzen im selben Host-Prozess melden sich hier an.
// So zeigt jedes Plugin-Fenster die komplette Bühne (alle Kanäle) und
// man kann jede Quelle von jedem Fenster aus verschieben.
class StageRegistry
{
public:
    static StageRegistry& get()
    {
        static StageRegistry instance;
        return instance;
    }

    int add (EarStageProcessor* p)
    {
        std::lock_guard<std::mutex> lock (mutex);
        instances.push_back (p);
        return ++counter;
    }

    void remove (EarStageProcessor* p)
    {
        std::lock_guard<std::mutex> lock (mutex);
        instances.erase (std::remove (instances.begin(), instances.end(), p), instances.end());
    }

    std::vector<EarStageProcessor*> snapshot() const
    {
        std::lock_guard<std::mutex> lock (mutex);
        return instances;
    }

    bool contains (EarStageProcessor* p) const
    {
        std::lock_guard<std::mutex> lock (mutex);
        return std::find (instances.begin(), instances.end(), p) != instances.end();
    }

private:
    mutable std::mutex mutex;
    std::vector<EarStageProcessor*> instances;
    int counter = 0;
};
