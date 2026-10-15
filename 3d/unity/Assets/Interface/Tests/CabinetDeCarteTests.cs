using System.Linq;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface.Tests
{
    public sealed class CabinetDeCarteTests
    {
        GameObject racine;
        CabinetDeCarte cabinet;
        [SetUp] public void Ouvrir()
        {
            racine = new GameObject("Carte de contrôle", typeof(CarteDessinee), typeof(HorlogeDeCarte), typeof(FicheDeCellule));
            cabinet = racine.AddComponent<CabinetDeCarte>();
            cabinet.Construire();
        }
        [TearDown] public void Fermer() => Object.DestroyImmediate(racine);

        [Test] public void LesDeuxDossiersRestentOuvertsEtLesPanneauxArretentLesClics()
        {
            foreach (var nom in new[] { "Votre maison", "Territoire conservé" })
            {
                var panneau = racine.GetComponentsInChildren<Image>().Single(p => p.name == nom);
                Assert.That(panneau.raycastTarget, Is.True);
                Assert.That(panneau.GetComponentInParent<GraphicRaycaster>(), Is.Not.Null);
            }
            cabinet.Construire();
            Assert.That(racine.GetComponentsInChildren<Canvas>().Length, Is.EqualTo(1));
        }

        [Test] public void SansHorlogeRecueLesCommandesDuTempsRestentInactives()
        {
            cabinet.Afficher();
            var boutons = racine.GetComponentsInChildren<Button>().Where(b => b.transform.parent.name == "FORGE · Le cabinet").ToArray();
            Assert.That(boutons.Length, Is.EqualTo(3));
            Assert.That(boutons.All(b => !b.interactable), Is.True);
        }

        [Test] public void UnTerritoireConserveSurvitALaFinDuSurvol()
        {
            cabinet.Garder(new CelluleDeCarte(7, new PolygoneDeCarte[0], new IdentiteDeCarte(1, "Puissance test"),
                null, new[] { new VilleDeCarte("Ville test", 12, new PointCarte(0, 0)) }));
            racine.GetComponent<FicheDeCellule>().Quitter();
            cabinet.Afficher();
            Assert.That(racine.GetComponentsInChildren<Text>().Any(t => t.text.Contains("Ville test") && t.text.Contains("en attente du monde")), Is.True);
        }
    }
}
