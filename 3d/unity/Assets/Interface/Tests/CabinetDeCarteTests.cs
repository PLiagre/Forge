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

        [Test] public void LaCommandeDesChantiersNeRecouvreAucuneCommandeVoisine()
        {
            var chantier = racine.GetComponentsInChildren<Button>(true).Single(b => b.name == "Chantiers");
            var cadre = chantier.GetComponent<RectTransform>();
            var zone = new Rect(cadre.anchoredPosition + cadre.rect.position, cadre.rect.size);
            foreach (var autre in chantier.transform.parent.GetComponentsInChildren<Button>(true))
            {
                if (autre == chantier || autre.transform.parent != chantier.transform.parent) continue;
                var rect = autre.GetComponent<RectTransform>();
                Assert.That(zone.Overlaps(new Rect(rect.anchoredPosition + rect.rect.position, rect.rect.size)),
                    Is.False, "Commande masquée : " + autre.name);
            }
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
        [TestCase(JOUEUR, 7L, 2L, true)] [TestCase(JOUEUR, 2L, 7L, false)] [TestCase(JOUEUR, 7L, 7L, false)] [TestCase(JOUEUR, 0L, 0L, false)] [TestCase(B, 7L, 2L, true)] [TestCase(B, 2L, 7L, false)] [TestCase(B, 7L, 7L, false)] [TestCase(B, 0L, 0L, false)] public void LeRougeSuitLeSolde(string maitre, long partis, long arrives, bool rouge)
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0)); Servir(_ => LectureLieu.De(Cellule(10, 3, Place(0, 1000, 2000, maitre, partis, arrives)))); var disque = Rendu(10, 0); Color attendu = rouge ? LieuxDeCarte.ROUGE : maitre == JOUEUR ? ReperesDeDepart.COULEUR_JOUEUR : LieuxDeCarte.CouleurDuMaitre(maitre); Assert.That(Disques() == 1 && disque != null && ((Color32)disque.sharedMaterial.color).Equals((Color32)attendu), Is.True, maitre + " " + partis + "/" + arrives); if (partis == 0 && arrives == 0) Assert.That(lieux.TexteLegende.Contains("absent"), Is.False, lieux.TexteLegende);
        }
        [Test] public void LeRougePeutDisparaitre()
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0));
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
        // Lot #658 : flèches du prélèvement et du dû.
        FlechesDeCarte fleches; const float R = ReperesDeDepart.DIAMETRE_BORD_KM / 2f;
        [Test] public void LeCabinetConstruitUneSeuleVueDesFleches() { Assert.That(racine.GetComponents<FlechesDeCarte>(), Has.Length.EqualTo(1)); cabinet.Construire(); Assert.That(racine.GetComponents<FlechesDeCarte>(), Has.Length.EqualTo(1)); }
        [TestCase(0d, 0f)] [TestCase(50000d, 1f)] [TestCase(218086d, 4.36172f)] [TestCase(400000d, 8f)] [TestCase(10000000d, 8f)] public void LEpaisseurEstAbsolueEtPlafonnee(double kg, float km) => Assert.That(FlechesDeCarte.Epaisseur(kg), Is.EqualTo(km).Within(1e-4f));
        [Test] public void UneFlecheParLieuTenuVersLeSiege()
        {
            Preparer(); fleches = racine.GetComponent<FlechesDeCarte>(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0));
            Func<long, LectureLieu> Lu(double a, FluxDeLieu f20) => cell => LectureLieu.De(cell == 10 ? Cellule(10, 5, new LieuPlace(0, new PointCarte(1, 2), JOUEUR, new FluxDeLieu(1234.4, 0, 0)), new LieuPlace(1, new PointCarte(30001, 2), JOUEUR, new FluxDeLieu(a, 0, 0)), new LieuPlace(2, new PointCarte(-29999, 2), B, new FluxDeLieu(90000, 0, 0)))
                : Cellule(20, 5, new LieuPlace(0, new PointCarte(1, 40002), JOUEUR, f20, f20 == null ? "flux non fournis" : null)));
            foreach (var (a, b) in new[] { (100000d, 218086d), (25000d, 400000d) })
            {
                Servir(Lu(a, new FluxDeLieu(b, 0, 0))); string t = fleches.TexteLegende; Assert.That(Fleches(), Is.EquivalentTo(new[] { "Flèche 10-1", "Flèche 20-0" }), t); Fleche("10-1", new PointCarte(30001, 2), a); Fleche("20-0", new PointCarte(1, 40002), b);
                Assert.That(t, Does.Contain(FlechesDeCarte.ENTETE).And.Contain("\nSiège : " + FlechesDeCarte.Kg(1234.4) + " prélevés sur place, sans flèche").And.Contain("\nLieu 10-1 → Siège : " + FlechesDeCarte.Kg(a)).And.Contain("\nLieu 20-0 → Siège : " + FlechesDeCarte.Kg(b)).And.Not.Contain("10-2"));
            }
            Servir(Lu(0, null)); Assert.That(Fleches(), Is.Empty); Assert.That(fleches.TexteLegende, Does.Contain("\nLieu 10-1 → Siège : 0 kg").And.Contain("\nLieu 20-0 → Siège : flux non fournis"));
            Servir(Lu(100000, new FluxDeLieu(1, 0, 0))); Assert.That(Fleches(), Has.Length.EqualTo(2)); Servir(cell => cell == 10 ? LectureLieu.Absent("refus témoin") : LectureLieu.De(new Lieu(20, 5, 1400, 1, 1, new Dictionary<string, double>(), 0, 0, absenceDesLieux: "lieux non servis"))); Assert.That(Fleches(), Is.Empty); Assert.That(fleches.TexteLegende, Does.Contain("\nAucune flèche de la cellule 10 : refus témoin").And.Contain("\nAucune flèche de la cellule 20 : lieux non servis").And.Not.Contain("Lieu 10-1").And.Not.Contain("Lieu 20-0"));
            Servir(Lu(100000, new FluxDeLieu(1, 0, 0))); Assert.That(Fleches(), Has.Length.EqualTo(2)); Publier(C, new LieuTenu(10, 0)); lieux.Pas(horloge); Assert.That(Fleches(), Is.Empty); Assert.That(fleches.TexteLegende, Does.Not.Contain("Lieu 10-1"));
        }
        [Test] public void LeDuPartVersLeSiegeDuSuzerain()
        {
            Preparer(); fleches = racine.GetComponent<FlechesDeCarte>(); int n = 0; fleches.Lecteur = _ => { n++; return null; }; fleches.Pas(0); Assert.That(n == 0 && !fleches.LectureEnVol, Is.True); Publier(JOUEUR, new LieuTenu(10, 0));
            MaisonLue M(string id, PointCarte? p, string raison = null) => new MaisonLue(id, id, new SiegeDeMaison(p == null ? (long?)null : 30, p == null ? (long?)null : 0, id == JOUEUR ? "Siège" : "Capitale", p), new LieuTenu[0], raison == null ? new Dictionary<string, string>() : new Dictionary<string, string> { ["siege"] = raison });
            Lecture<ComptesDeMaison> Comptes(string id, PointCarte? p, string suzerain, string raison = null) => Lecture<ComptesDeMaison>.De(new ComptesDeMaison(M(id, p, raison), suzerain, 0.6, null, new FluxDeMaison(999999, 0, id == JOUEUR ? 76788.18 : 5, 0, 0, 0, 0, null)));
            PointCarte haut = new PointCarte(60001, 50002), siege = new PointCarte(1, 2); Func<string, Lecture<ComptesDeMaison>> bon = id => id == JOUEUR ? Comptes(JOUEUR, siege, B) : Comptes(B, haut, null);
            var etapes = new (Func<string, Lecture<ComptesDeMaison>>, string)[] { (bon, "\nSiège → Capitale : " + FlechesDeCarte.Kg(76788.18) + " de dû"), (_ => Comptes(JOUEUR, siege, null), "\nDû au suzerain : sans suzerain : aucun dû"),
                (id => id == JOUEUR ? Comptes(JOUEUR, siege, B) : Comptes(B, null, null, "siège non servi"), "\nDû au suzerain : siège du suzerain hors carte : siège non servi"), (_ => Lecture<ComptesDeMaison>.Absent("refus témoin"), "\nDû au suzerain : lecture refusée : refus témoin"), (bon, "Capitale : ") };
            foreach (var (lire, texte) in etapes) { Du(lire); bool vue = lire == bon; Assert.That(fleches.TexteLegende, Does.Contain(texte)); Assert.That(Fleches(), Is.EqualTo(vue ? new[] { FlechesDeCarte.DU } : new string[0]), texte); if (vue) Fleche("du dû", siege, 76788.18, haut); }
            var porte = new System.Threading.Tasks.TaskCompletionSource<Lecture<ComptesDeMaison>>(); Du(_ => Comptes(JOUEUR, siege, null)); fleches.Lecteur = id => id == JOUEUR ? porte.Task.Result : bon(id); fleches.Pas(horloge); Assert.That(fleches.LectureEnVol, Is.True);
            Publier(C, new LieuTenu(10, 0)); fleches.Pas(horloge); porte.SetResult(Comptes(JOUEUR, siege, B)); var fin = DateTime.UtcNow.AddSeconds(5); while (fleches.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); fleches.Pas(horloge);
            Assert.That(Fleches(), Is.Empty); Assert.That(fleches.TexteLegende, Does.Not.Contain("kg de dû"));
        }
        void Du(Func<string, Lecture<ComptesDeMaison>> lire) { fleches.Lecteur = lire; fleches.Pas(horloge); var fin = DateTime.UtcNow.AddSeconds(5); while (fleches.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); Assert.That(fleches.LectureEnVol, Is.False); fleches.Pas(horloge); horloge += FlechesDeCarte.PERIODE_S; }
        string[] Fleches() { var r = racine.transform.Find(FlechesDeCarte.RACINE); return r == null ? new string[0] : r.Cast<Transform>().Select(e => e.name).ToArray(); }
        void Fleche(string nom, PointCarte depart, double kg, PointCarte? arrivee = null)
        {
            var f = racine.transform.Find(FlechesDeCarte.RACINE + "/Flèche " + nom); var v = f.GetComponent<MeshFilter>().sharedMesh.vertices; Vector3 a = carte.PositionSurLaCarte(depart, FlechesDeCarte.HAUTEUR).Value, b = carte.PositionSurLaCarte(arrivee ?? new PointCarte(1, 2), FlechesDeCarte.HAUTEUR).Value, pied = (v[0] + v[3]) / 2f;
            Assert.That(Mathf.Abs(Vector3.Distance(pied, a) - R) < 1e-2f && Mathf.Abs(Vector3.Distance(v[5], b) - R) < 1e-2f && Vector3.Dot(v[5] - pied, b - a) > 0f && f.GetComponent<Collider>() == null, Is.True, nom + " pied " + pied + " pointe " + v[5]);
            Assert.That(Vector3.Distance(v[0], v[3]), Is.EqualTo(FlechesDeCarte.Epaisseur(kg)).Within(1e-2f), nom); Assert.That((Color32)f.GetComponent<MeshRenderer>().sharedMaterial.color, Is.EqualTo((Color32)(nom == "du dû" ? FlechesDeCarte.VIOLET : FlechesDeCarte.ORANGE)));
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
