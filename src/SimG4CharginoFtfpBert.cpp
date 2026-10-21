// FCC-hh disappearing-track tutorial
//
// A modern k4SimGeant4 physics-list tool based on FTFP_BERT that defines
// neutralino and chargino states and, optionally, the two-body decay
//
//   chi+ -> chi0 + pi+
//   chi- -> chi0 + pi-
//
// The implementation follows the current ISimG4PhysicsList interface.
// It deliberately keeps the model minimal: it is intended for detector/
// tracking studies, not as a general SUSY Geant4 model.

#include "GaudiKernel/AlgTool.h"
#include "SimG4Interface/ISimG4PhysicsList.h"

#include "FTFP_BERT.hh"
#include "G4DecayTable.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"
#include "G4PhaseSpaceDecayChannel.hh"
#include "G4SystemOfUnits.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VPhysicsConstructor.hh"
#include "G4ProcessManager.hh"
#include "G4VProcess.hh"
#include "G4ios.hh"
#include "G4hMultipleScattering.hh"
#include "G4hIonisation.hh"

#include <memory>

class CharginoParticlePhysics final : public G4VPhysicsConstructor {
public:
  CharginoParticlePhysics(double neutralinoMassGeV,
                          double charginoPlusMassGeV,
                          double charginoMinusMassGeV,
                          double charginoPlusLifetimeNs,
                          double charginoMinusLifetimeNs,
                          bool stableChargino)
      : G4VPhysicsConstructor("CharginoParticlePhysics"),
        m_neutralinoMass(neutralinoMassGeV * GeV),
        m_charginoPlusMass(charginoPlusMassGeV * GeV),
        m_charginoMinusMass(charginoMinusMassGeV * GeV),
        m_charginoPlusLifetime(charginoPlusLifetimeNs * ns),
        m_charginoMinusLifetime(charginoMinusLifetimeNs * ns),
        m_stableChargino(stableChargino) {}

  void ConstructParticle() override {
    auto* table = G4ParticleTable::GetParticleTable();

    // Neutralino: stable, neutral, PDG 1000022.
    if (!table->FindParticle(1000022)) {
      new G4ParticleDefinition(
          "neutralino1", m_neutralinoMass, 0.0, 0.0,
          1, +1, 0, 0, 0, 0,
          "supersymmetric", 0, 0, 1000022,
          true, -1.0, nullptr, false, "neutralino");
    }

    if (!table->FindParticle(1000024)) {
      auto* chiPlus = new G4ParticleDefinition(
          "chargino+", m_charginoPlusMass, 0.0, +1.0 * eplus,
          1, +1, 0, 0, 0, 0,
          "supersymmetric", 0, 0, 1000024,
          m_stableChargino, m_stableChargino ? -1.0 : m_charginoPlusLifetime,
          nullptr, false, "chargino");

      if (!m_stableChargino) {
        auto* decays = new G4DecayTable();
        decays->Insert(new G4PhaseSpaceDecayChannel(
            "chargino+", 1.0, 2, "neutralino1", "pi+"));
        chiPlus->SetDecayTable(decays);
      }
    }

    if (!table->FindParticle(-1000024)) {
      auto* chiMinus = new G4ParticleDefinition(
          "chargino-", m_charginoMinusMass, 0.0, -1.0 * eplus,
          1, +1, 0, 0, 0, 0,
          "supersymmetric", 0, 0, -1000024,
          m_stableChargino, m_stableChargino ? -1.0 : m_charginoMinusLifetime,
          nullptr, false, "chargino");

      if (!m_stableChargino) {
        auto* decays = new G4DecayTable();
        decays->Insert(new G4PhaseSpaceDecayChannel(
            "chargino-", 1.0, 2, "neutralino1", "pi-"));
        chiMinus->SetDecayTable(decays);
      }
    }
  }

  void ConstructProcess() override {

    auto* table = G4ParticleTable::GetParticleTable();

    for (const auto& name : {"chargino+", "chargino-"}) {

      auto* particle = table->FindParticle(name);

      G4cout << "\n========================================" << G4endl;
      G4cout << "Processes for " << name << G4endl;
      G4cout << "========================================" << G4endl;

      if (!particle) {
        G4cout << "ERROR: particle not found" << G4endl;
        continue;
      }

      G4cout << "PDG:      "
            << particle->GetPDGEncoding() << G4endl;

      G4cout << "Mass:     "
            << particle->GetPDGMass() / GeV
            << " GeV" << G4endl;

      G4cout << "Charge:   "
            << particle->GetPDGCharge() / eplus
            << " e" << G4endl;

      G4cout << "Stable:   "
            << particle->GetPDGStable() << G4endl;

      G4cout << "Lifetime: "
            << particle->GetPDGLifeTime() / ns
            << " ns" << G4endl;

      auto* pm = particle->GetProcessManager();

      if (!pm) {
        G4cout << "NO PROCESS MANAGER" << G4endl;
        continue;
      }
      // Add electromagnetic interactions for the heavy charged particle.
      pm->AddProcess(new G4hMultipleScattering(), -1, 1, 1);
      pm->AddProcess(new G4hIonisation(),        -1, 2, 2);

      // Diagnostic printout.
      G4cout << "\n========================================" << G4endl;
      G4cout << "Processes for " << name << G4endl;
      G4cout << "========================================" << G4endl;

      G4cout << "PDG:      "
            << particle->GetPDGEncoding() << G4endl;

      G4cout << "Mass:     "
            << particle->GetPDGMass() / GeV
            << " GeV" << G4endl;

      G4cout << "Charge:   "
            << particle->GetPDGCharge() / eplus
            << " e" << G4endl;

      G4cout << "Stable:   "
            << particle->GetPDGStable() << G4endl;

      G4cout << "Lifetime: "
            << particle->GetPDGLifeTime() / ns
            << " ns" << G4endl;

      auto* processes = pm->GetProcessList();

      G4cout << "Number of processes: "
            << processes->size() << G4endl;

      for (std::size_t i = 0; i < processes->size(); ++i) {
        G4cout << "  "
              << (*processes)[i]->GetProcessName()
              << G4endl;

        // Turn on verbose output specifically for the decay process
        if ((*processes)[i]->GetProcessName() == "Decay") {
          (*processes)[i]->SetVerboseLevel(0);
              
        }
      }  
    }
  }

private:
  double m_neutralinoMass;
  double m_charginoPlusMass;
  double m_charginoMinusMass;
  double m_charginoPlusLifetime;
  double m_charginoMinusLifetime;
  bool m_stableChargino;
};

class SimG4CharginoFtfpBert final : public AlgTool,
                                    virtual public ISimG4PhysicsList {
public:
  SimG4CharginoFtfpBert(const std::string& type,
                        const std::string& name,
                        const IInterface* parent)
      : AlgTool(type, name, parent) {
    declareInterface<ISimG4PhysicsList>(this);
  }

  StatusCode initialize() override { return AlgTool::initialize(); }
  StatusCode finalize() override { return AlgTool::finalize(); }

  G4VModularPhysicsList* physicsList() override {
    auto* list = new FTFP_BERT(m_g4Verbosity.value());

    list->RegisterPhysics(new CharginoParticlePhysics(
        m_neutralinoMassGeV.value(),
        m_charginoPlusMassGeV.value(),
        m_charginoMinusMassGeV.value(),
        m_charginoPlusLifetimeNs.value(),
        m_charginoMinusLifetimeNs.value(),
        m_stableChargino.value()));

    return list;
  }

private:
  Gaudi::Property<double> m_neutralinoMassGeV{
      this, "NeutralinoMassGeV", 3000.0, "Neutralino mass [GeV]"};

  Gaudi::Property<double> m_charginoPlusMassGeV{
      this, "CharginoPlusMassGeV", 3000.165, "Positive chargino mass [GeV]"};

  Gaudi::Property<double> m_charginoMinusMassGeV{
      this, "CharginoMinusMassGeV", 3000.165, "Negative chargino mass [GeV]"};

  Gaudi::Property<double> m_charginoPlusLifetimeNs{
      this, "CharginoPlusLifetimeNs", 0.2, "Positive chargino proper lifetime [ns]"};

  Gaudi::Property<double> m_charginoMinusLifetimeNs{
      this, "CharginoMinusLifetimeNs", 0.2, "Negative chargino proper lifetime [ns]"};

  Gaudi::Property<bool> m_stableChargino{
      this, "StableChargino", false,
      "If true, do not decay the chargino in Geant4"};

  Gaudi::Property<int> m_g4Verbosity{
      this, "G4PhysicsVerbosityLevel", 0, "Geant4 physics verbosity"};
};

// In Gaudi 40 this macro is available through the standard Gaudi component
// headers included by AlgTool. Do not include the removed
// GaudiKernel/ComponentFactory.h header.
DECLARE_COMPONENT(SimG4CharginoFtfpBert)
