using System; using Object = UnityEngine.Object;
using System.Collections.Generic;
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
            racine = new GameObject("Carte de contrôle", typeof(CarteDessinee), typeof(HorlogeDeCarte), typeof(FicheDeCellule), typeof(ReperesDeDepart));
            cabinet = racine.AddComponent<CabinetDeCarte>();
            cabinet.Construire();
        }
        [TearDown] public void Fermer() => Object.DestroyImmediate(racine);

        [Test] public void LeChoixDirectDuPrototypeEstArrete()
        {
            var prototype = racine.GetComponent<ReperesDeDepart>();
            Assert.That(prototype.enabled, Is.False);
            prototype.Choisir(Vector2.zero);
            Assert.That(prototype.ChoixEnVol, Is.False);
        }

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

        const string JOUEUR = "maison-joueur", B = "maison-b", C = "maison-c";
        LieuxDeCarte lieux; CarteDessinee carte; LecturePartie partie; Camera camera; Material cellule; MeshRenderer celluleRendu; double horloge;
        [Test] public void LeCabinetConstruitUneSeuleVueDesLieux() { int avant = racine.GetComponents<MonoBehaviour>().Length; Assert.That(racine.GetComponents<LieuxDeCarte>(), Has.Length.EqualTo(1)); cabinet.Construire(); Assert.That(racine.GetComponents<LieuxDeCarte>(), Has.Length.EqualTo(1)); Assert.That(racine.GetComponents<MonoBehaviour>().Length, Is.EqualTo(avant)); }
        [Test] public void TousLesLieuxDesCellulesTenuesOntLeurCouleur()
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); var vus = new List<long>(); var couleurs = new Dictionary<string, Color32>();
            Servir(cell => { vus.Add(cell); return Reponse(cell, 4, false); }); Assert.That(vus, Is.EquivalentTo(new[] { 10L, 20L }), lieux.TexteLegende + " disques " + Disques()); Assert.That(Disques(), Is.EqualTo(5)); Assert.That(lieux.TexteLegende, Does.Contain("Cellule 10 au tick 4").And.Contain("Cellule 20 au tick 4").And.Contain(LieuxDeCarte.ENTETE));
            foreach (var (cell, rang, x, y, maitre) in Attendu()) { var disque = Rendu(cell, rang); var bord = disque.transform.parent.Find("Bord").GetComponent<MeshRenderer>(); Color couleur = maitre == JOUEUR ? ReperesDeDepart.COULEUR_JOUEUR : LieuxDeCarte.CouleurDuMaitre(maitre); couleurs[cell + "-" + rang] = disque.sharedMaterial.color; Assert.That(disque.transform.parent.localPosition, Is.EqualTo(carte.PositionSurLaCarte(new PointCarte(x, y), ReperesDeDepart.HAUTEUR_LIEU).Value)); Assert.That((Color32)disque.sharedMaterial.color, Is.EqualTo((Color32)couleur)); Assert.That(bord.gameObject.activeInHierarchy && bord.sharedMaterial.color.maxColorComponent < 0.25f && disque.GetComponent<Collider>() == null, Is.True, cell + "-" + rang); }
            Assert.That(Rendu(10, 1).sharedMaterial, Is.SameAs(Rendu(20, 0).sharedMaterial)); Assert.That(Rendu(10, 0).sharedMaterial, Is.SameAs(Rendu(20, 1).sharedMaterial)); Assert.That((Color32)Rendu(10, 2).sharedMaterial.color, Is.Not.EqualTo((Color32)Rendu(10, 1).sharedMaterial.color)); Assert.That((Color32)Rendu(10, 2).sharedMaterial.color, Is.Not.EqualTo((Color32)LieuxDeCarte.ROUGE));
            vus.Clear(); Servir(cell => { vus.Add(cell); return Reponse(cell, 11, true); }); Assert.That(vus, Is.EquivalentTo(new[] { 10L, 20L })); Assert.That(lieux.TexteLegende, Does.Contain("au tick 11")); foreach (var (cell, rang, _, _, _) in Attendu()) Assert.That((Color32)Rendu(cell, rang).sharedMaterial.color, Is.EqualTo(couleurs[cell + "-" + rang]), "inverse " + cell);
            Servir(cell => Reponse(cell, 12, false)); Assert.That(Disques(), Is.EqualTo(5)); Assert.That(lieux.TexteLegende, Does.Contain("au tick 12")); foreach (var (cell, rang, _, _, _) in Attendu()) Assert.That((Color32)Rendu(cell, rang).sharedMaterial.color, Is.EqualTo(couleurs[cell + "-" + rang]), "tick 12 " + cell);
        }
        [Test] public void LeRougeSuitLeSoldeEtPeutDisparaitre()
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0));
            foreach (string maitre in new[] { JOUEUR, B }) foreach (var (partis, arrives, rouge) in new[] { (7L, 2L, true), (2L, 7L, false), (7L, 7L, false), (0L, 0L, false) }) { Servir(_ => LectureLieu.De(Cellule(10, 3, Place(0, 1000, 2000, maitre, partis, arrives)))); var disque = Rendu(10, 0); Color attendu = rouge ? LieuxDeCarte.ROUGE : maitre == JOUEUR ? ReperesDeDepart.COULEUR_JOUEUR : LieuxDeCarte.CouleurDuMaitre(maitre); Assert.That(Disques() == 1 && disque != null && ((Color32)disque.sharedMaterial.color).Equals((Color32)attendu), Is.True, maitre + " " + partis + "/" + arrives); if (partis == 0 && arrives == 0) Assert.That(lieux.TexteLegende.Contains("absent"), Is.False, lieux.TexteLegende); }
            Material rougeMat = null, maitreMat = null; long tick = 4; FluxDeLieu flux = new FluxDeLieu(0, 7, 2); string cause = null;
            for (int etape = 0; etape < 4; etape++) { if (etape == 1) { flux = new FluxDeLieu(0, 7, 7); tick = 5; } if (etape == 2) { flux = null; cause = "flux non fournis"; tick = 6; } if (etape == 3) { flux = new FluxDeLieu(0, 7, 2); cause = null; tick = 7; } Servir(_ => LectureLieu.De(Cellule(10, tick, new LieuPlace(0, new PointCarte(1000, 2000), JOUEUR, flux, cause)))); var mat = Rendu(10, 0).sharedMaterial; if (etape == 0) { rougeMat = mat; Assert.That((Color32)mat.color, Is.EqualTo((Color32)LieuxDeCarte.ROUGE)); } if (etape == 1) { maitreMat = mat; Assert.That(mat, Is.Not.SameAs(rougeMat)); Assert.That((Color32)mat.color, Is.EqualTo((Color32)ReperesDeDepart.COULEUR_JOUEUR)); } if (etape == 2) Assert.That(mat == maitreMat && lieux.TexteLegende.Contains("Cellule 10, rang 0 : flux non fournis") && lieux.TexteLegende.Contains("au tick 6"), Is.True, lieux.TexteLegende); if (etape == 3) Assert.That(mat == rougeMat && !lieux.TexteLegende.Contains("flux non fournis") && lieux.TexteLegende.Contains("au tick 7"), Is.True, lieux.TexteLegende); Assert.That(Disques(), Is.EqualTo(1)); }
        }
        [Test] public void LesAbsencesEtLaNavigationRestentHonnetes()
        {
            Preparer(); int n = 0; lieux.Lecteur = _ => { n++; return null; }; lieux.Pas(0); lieux.Pas(3); Assert.That(n == 0 && Disques() == 0, Is.True);
            var porte = new System.Threading.Tasks.TaskCompletionSource<bool>(); lieux.Lecteur = cell => { System.Threading.Interlocked.Increment(ref n); porte.Task.Wait(8000); return Complet(cell, 3); };
            Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(20, 0)); lieux.Pas(0); var fin = DateTime.UtcNow.AddSeconds(5); while (n < 1 && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); lieux.Pas(1); Assert.That(n, Is.EqualTo(1), lieux.TexteLegende);
            Publier("maison-ancienne", new LieuTenu(10, 0), new LieuTenu(20, 0)); porte.TrySetResult(true); fin = DateTime.UtcNow.AddSeconds(5); while (lieux.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); lieux.Pas(1);
            Assert.That(Disques() == 0 && n == 2 && !lieux.LectureEnVol, Is.True, lieux.TexteLegende); horloge = 2; Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); Servir(cell => Complet(cell, 8)); Assert.That(Rendu(10, 0) != null && Rendu(20, 0) != null, Is.True);
            void Reprise(Func<long, LectureLieu> mauvais, Func<bool> bon, string texte) { Servir(mauvais); Assert.That(bon() && lieux.TexteLegende.Contains(texte), Is.True, lieux.TexteLegende); Servir(cell => Complet(cell, 8)); }
            Reprise(cell => cell == 10 ? LectureLieu.Absent("lecture refusée") : Complet(cell, 8), () => Rendu(10, 0) == null && Rendu(10, 1) == null && Rendu(20, 0) != null, "lecture refusée");
            Reprise(cell => cell == 10 ? LectureLieu.De(Cellule(10, 8)) : Complet(cell, 8), () => Rendu(10, 0) == null && Rendu(20, 0) != null, "liste vide");
            Reprise(cell => cell == 10 ? LectureLieu.De(new Lieu(10, 8, 1400, 1, 1, new Dictionary<string, double>(), 0, 0, lieux: null, absenceDesLieux: "clé absente : lieux")) : Complet(cell, 8), () => Rendu(10, 0) == null && Rendu(20, 0) != null, "clé absente : lieux");
            Reprise(cell => cell == 10 ? LectureLieu.De(Cellule(10, 8, Place(0, 1000, 2000, JOUEUR, 1, 2), new LieuPlace(1, null, B, new FluxDeLieu(0, 1, 1)))) : Complet(cell, 8), () => Rendu(10, 0) != null && Rendu(10, 1) == null && Rendu(20, 0) != null, "Cellule 10, rang 1 : point absent");
            Reprise(cell => cell == 10 ? LectureLieu.De(Cellule(10, 8, Place(0, 1000, 2000, JOUEUR, 1, 2), new LieuPlace(1, new PointCarte(4000, 2000), null, new FluxDeLieu(0, 1, 1)))) : Complet(cell, 8), () => Rendu(10, 1) == null && Rendu(10, 0) != null, "Cellule 10, rang 1 : maître absent");
            Vector2 centre = carte.Vue.Centre; float echelle = carte.Vue.Echelle; Vector3 pos = camera.transform.position; Color teinte = cellule.color; int nombre = Disques(); Servir(cell => Complet(cell, 9)); Servir(cell => Complet(cell, 10)); Servir(cell => Complet(cell, 11));
            Assert.That(Disques() == nombre && carte.Vue.Centre == centre && carte.Vue.Echelle == echelle && camera.transform.position == pos && celluleRendu.sharedMaterial == cellule && cellule.color == teinte, Is.True); Assert.That(racine.transform.Find(LieuxDeCarte.RACINE).GetComponentsInChildren<Collider>(true), Is.Empty);
        }
        void Preparer() { horloge = 0; lieux = racine.GetComponent<LieuxDeCarte>(); carte = racine.GetComponent<CarteDessinee>(); typeof(CarteDessinee).GetField("origine", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic).SetValue(carte, (PointCarte?)new PointCarte(3000000, 1500000)); Poser(carte, "Vue", new VueDeCarte(new Bounds(Vector3.zero, new Vector3(8000f, 1f, 6000f)), 1.6f)); camera = new GameObject("caméra témoin").AddComponent<Camera>(); camera.transform.SetParent(racine.transform, false); camera.transform.position = new Vector3(3, 4, 5); carte.camera = camera; celluleRendu = new GameObject("Cellule 10").AddComponent<MeshRenderer>(); celluleRendu.transform.SetParent(racine.transform, false); cellule = new Material(UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline.defaultMaterial) { color = Color.green }; celluleRendu.sharedMaterial = cellule; Assert.That(carte.Vue != null && carte.PositionSurLaCarte(new PointCarte(1, 1), 0f) != null, Is.True); }
        void Publier(string id, params LieuTenu[] tenus) { if (partie == null) partie = new LecturePartie(() => null, _ => null, () => null, _ => null); cabinet.Partie = partie; Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(1, new DateDuMonde(1400, 1), 0, new CelluleDuMonde[0]), id))); Poser(partie, "Maison", Lecture<MaisonLue>.De(new MaisonLue(id, "Maison", new SiegeDeMaison(tenus[0].CellId, tenus[0].Rang, "Siège", new PointCarte(1, 2)), tenus, new Dictionary<string, string>()))); }
        static void Poser(object cible, string nom, object valeur) => cible.GetType().GetProperty(nom).GetSetMethod(true).Invoke(cible, new[] { valeur });
        void Servir(Func<long, LectureLieu> lire) { lieux.Lecteur = lire; lieux.Pas(horloge); var fin = DateTime.UtcNow.AddSeconds(5); while (lieux.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); Assert.That(lieux.LectureEnVol, Is.False, lieux.TexteLegende); lieux.Pas(horloge); horloge += LieuxDeCarte.PERIODE_S; }
        static (long, long, double, double, string)[] Attendu() => new[] { (10L, 0L, 1000d, 2000d, JOUEUR), (10L, 1L, 5000d, 2500d, B), (10L, 2L, 1500d, 7000d, C), (20L, 0L, 9000d, 1000d, B), (20L, 1L, 12000d, 4000d, JOUEUR) };
        static LectureLieu Reponse(long cell, long tick, bool inverse) { var tous = Attendu().Where(p => p.Item1 == cell).Select(p => Place(p.Item2, p.Item3, p.Item4, p.Item5, 1, 2)).ToArray(); if (inverse) Array.Reverse(tous); return LectureLieu.De(Cellule(cell, tick, tous)); }
        static LectureLieu Complet(long cell, long tick) => cell == 20 ? LectureLieu.De(Cellule(20, tick, Place(0, 8000, 3000, JOUEUR, 0, 1))) : cell == 10 ? LectureLieu.De(Cellule(10, tick, Place(0, 1000, 2000, JOUEUR, 1, 2), Place(1, 4000, 2000, B, 1, 1))) : LectureLieu.Absent("cellule extérieure " + cell);
        static Lieu Cellule(long cell, long tick, params LieuPlace[] places) => new Lieu(cell, tick, 1400, 1, 1, new Dictionary<string, double>(), 0, 0, lieux: places);
        static LieuPlace Place(long rang, double x, double y, string maitre, long partis, long arrives) => new LieuPlace(rang, new PointCarte(x, y), maitre, new FluxDeLieu(0, partis, arrives));
        MeshRenderer Rendu(long cell, long rang) { var t = racine.transform.Find(LieuxDeCarte.RACINE + "/" + ReperesDeDepart.NomDuLieu(cell, rang) + "/Disque"); return t != null && t.gameObject.activeInHierarchy ? t.GetComponent<MeshRenderer>() : null; }
        int Disques() { var r = racine.transform.Find(LieuxDeCarte.RACINE); if (r == null) return 0; int n = 0; foreach (Transform e in r) { var d = e.Find("Disque"); if (d != null && d.gameObject.activeInHierarchy) n++; } return n; }
    }
}
