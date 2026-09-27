using System.Collections;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Victoria.CityMode.Tests
{
    public sealed class CityLabPlayModeTests
    {
        [UnityTest]
        public IEnumerator Bootstrap_CreatesPlayableWorld()
        {
            SceneManager.LoadScene("CityLab", LoadSceneMode.Single);
            yield return null;
            yield return null;

            var game = Object.FindFirstObjectByType<CityLabGame>();
            Assert.IsNotNull(game, "Le bootstrap doit creer CityLabGame.");
            Assert.IsNotNull(game.WorldCamera, "La camera RTS doit exister.");
            Assert.IsNotNull(Object.FindFirstObjectByType<Terrain>(), "Le terrain 512 m doit exister.");
            Assert.IsNotNull(Object.FindFirstObjectByType<CityLabHud>(), "Le HUD UI Toolkit doit exister.");
            var visuals = Resources.Load<CityVisualLibrary>("CityLabVisualLibrary");
            Assert.IsNotNull(visuals, "Le catalogue d'assets admis doit être chargé depuis l'hôte.");
            Assert.IsTrue(visuals.HasDurableSlice, "Le catalogue visuel doit contenir le slice durable.");

            var road = game.Submit(CityCommand.DrawRoad(new Vector3(-30f, 0f, 8f), new Vector3(30f, 0f, 8f)));
            Assert.IsTrue(road.accepted);
            Assert.IsTrue(game.Submit(CityCommand.ZoneResidential(road.createdId)).accepted);
            yield return null;

            var snapshot = game.StateSource.GetSnapshot(1001);
            Assert.Greater(snapshot.parcels.Count, 0);
            Assert.Greater(snapshot.buildings.Count, 0);
            var roadView = Object.FindFirstObjectByType<RoadView>();
            Assert.IsNotNull(roadView);
            var roadMesh = roadView.GetComponent<MeshFilter>();
            Assert.IsNotNull(roadMesh, "La route doit etre un ruban maille conforme au terrain.");
            Assert.Greater(roadMesh.sharedMesh.vertexCount, 4);

            var camp = game.Submit(CityCommand.PlaceLumberCamp(new Vector3(70f, 0f, 0f)));
            Assert.IsTrue(camp.accepted);
            yield return null;
            var productionSites = game.StateSource.GetSnapshot(1001).productionSites;
            Assert.AreEqual(1, productionSites.Count(item => item.kind == ProductionSiteKind.LumberCamp));
            Assert.AreEqual(7, productionSites.Count(item => item.kind != ProductionSiteKind.LumberCamp));
            Assert.IsNotNull(Object.FindFirstObjectByType<LumberCampVisual>(),
                "Le camp forestier doit avoir une presentation dans le monde.");

            var granary = game.Submit(CityCommand.PlaceBuilding(
                BuildingArchetype.Granary, new Vector3(-70f, 0f, 70f)));
            Assert.IsTrue(granary.accepted, granary.reason);
            yield return null;
            var granaryState = game.StateSource.GetSnapshot(1001).buildings
                .Find(item => item.id == granary.createdId);
            Assert.IsNotNull(granaryState);
            Assert.AreEqual(BuildingArchetype.Granary, granaryState.archetype);
            var granaryView = Object.FindObjectsByType<BuildingView>(FindObjectsSortMode.None)
                .FirstOrDefault(item => item.BuildingId == granary.createdId);
            Assert.IsNotNull(granaryView);
            var scaffold = granaryView.GetComponent<ConstructionScaffoldVisual>();
            Assert.IsNotNull(scaffold, "Chaque chantier civique doit porter son échafaudage.");

            var controller = Object.FindFirstObjectByType<CityBuildController>();
            Assert.IsNotNull(controller);
            var selectedId = granary.createdId;
            controller.SelectBuilding(selectedId);
            controller.SetSelectedPriority(3);
            yield return null;
            Assert.AreEqual(selectedId, controller.SelectedBuildingId);
            Assert.AreEqual(3, game.StateSource.GetSnapshot(1001).buildings.Find(item => item.id == selectedId).priority);
            Assert.IsTrue(granaryView.IsSelected);
            Assert.IsTrue(scaffold.IsSelected,
                "La sélection du chantier doit atteindre son échafaudage.");

            var serialized = CitySaveService.Serialize(game.StateSource.GetSnapshot(1001));
            Assert.IsTrue(CitySaveService.TryDeserialize(serialized,
                out var reloadedSnapshot, out var reloadReason), reloadReason);
            var restore = typeof(CityLabGame).GetMethod("RestoreSnapshot",
                BindingFlags.Instance | BindingFlags.NonPublic);
            Assert.IsNotNull(restore);
            restore.Invoke(game, new object[] { reloadedSnapshot });
            yield return null;

            var reloadedView = Object.FindObjectsByType<BuildingView>(FindObjectsSortMode.None)
                .FirstOrDefault(item => item.BuildingId == selectedId);
            Assert.IsNotNull(reloadedView);
            var reloadedScaffold = reloadedView.GetComponent<ConstructionScaffoldVisual>();
            Assert.IsNotNull(reloadedScaffold);
            Assert.AreEqual(reloadedSnapshot.buildings.Find(item => item.id == selectedId).phase,
                reloadedScaffold.CurrentPhase);
            Assert.IsTrue(reloadedView.IsSelected,
                "Le rechargement doit réappliquer le surlignage du chantier sélectionné.");
            Assert.IsTrue(reloadedScaffold.IsSelected,
                "Le rechargement doit réappliquer les marqueurs de l'échafaudage sélectionné.");

            game.SetSimulationSpeed(2f);
            Assert.AreEqual(2f, game.SimulationSpeed);
            game.TogglePause();
            Assert.IsTrue(game.IsPaused);
            game.TogglePause();
            Assert.AreEqual(2f, game.SimulationSpeed);
        }
    }
}
