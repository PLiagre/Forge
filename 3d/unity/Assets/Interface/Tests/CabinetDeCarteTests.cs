using System; using Object = UnityEngine.Object;
using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
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
            Servir(cell => { vus.Add(cell); return Reponse(cell, 4, false); }); Assert.That(vus, Is.EquivalentTo(new[] { 10L, 20L }), lieux.TexteLegende + " disques " + Disques()); Assert.That(Disques(), Is.EqualTo(5)); Assert.That(lieux.TexteLegende, Does.Contain("\nAlba · relevé au jour 5 de 1400").And.Contain("\nDara · relevé au jour 5 de 1400").And.Contain(LieuxDeCarte.ENTETE));
            foreach (var (cell, rang, x, y, maitre) in Attendu()) { var disque = Rendu(cell, rang); var bord = disque.transform.parent.Find("Bord").GetComponent<MeshRenderer>(); Color couleur = maitre == JOUEUR ? ReperesDeDepart.COULEUR_JOUEUR : LieuxDeCarte.CouleurDuMaitre(maitre); couleurs[cell + "-" + rang] = disque.sharedMaterial.color; Assert.That(disque.transform.parent.localPosition, Is.EqualTo(carte.PositionSurLaCarte(new PointCarte(x, y), ReperesDeDepart.HAUTEUR_LIEU).Value)); Assert.That((Color32)disque.sharedMaterial.color, Is.EqualTo((Color32)couleur)); Assert.That(bord.gameObject.activeInHierarchy && bord.sharedMaterial.color.maxColorComponent < 0.25f && disque.GetComponent<Collider>() == null, Is.True, cell + "-" + rang); }
            Assert.That(Rendu(10, 1).sharedMaterial, Is.SameAs(Rendu(20, 0).sharedMaterial)); Assert.That(Rendu(10, 0).sharedMaterial, Is.SameAs(Rendu(20, 1).sharedMaterial)); Assert.That((Color32)Rendu(10, 2).sharedMaterial.color, Is.Not.EqualTo((Color32)Rendu(10, 1).sharedMaterial.color)); Assert.That((Color32)Rendu(10, 2).sharedMaterial.color, Is.Not.EqualTo((Color32)LieuxDeCarte.ROUGE));
            vus.Clear(); Servir(cell => { vus.Add(cell); return Reponse(cell, 11, true); }); Assert.That(vus, Is.EquivalentTo(new[] { 10L, 20L })); Assert.That(lieux.TexteLegende, Does.Contain("relevé au jour 12 de 1400")); foreach (var (cell, rang, _, _, _) in Attendu()) Assert.That((Color32)Rendu(cell, rang).sharedMaterial.color, Is.EqualTo(couleurs[cell + "-" + rang]), "inverse " + cell);
            Servir(cell => Reponse(cell, 12, false)); Assert.That(Disques(), Is.EqualTo(5)); Assert.That(lieux.TexteLegende, Does.Contain("relevé au jour 13 de 1400")); foreach (var (cell, rang, _, _, _) in Attendu()) Assert.That((Color32)Rendu(cell, rang).sharedMaterial.color, Is.EqualTo(couleurs[cell + "-" + rang]), "tick 12 " + cell);
        }
        [TestCase(JOUEUR, 7L, 2L, true)] [TestCase(JOUEUR, 2L, 7L, false)] [TestCase(JOUEUR, 7L, 7L, false)] [TestCase(JOUEUR, 0L, 0L, false)] [TestCase(B, 7L, 2L, true)] [TestCase(B, 2L, 7L, false)] [TestCase(B, 7L, 7L, false)] [TestCase(B, 0L, 0L, false)] public void LeRougeSuitLeSolde(string maitre, long partis, long arrives, bool rouge)
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0)); Servir(_ => LectureLieu.De(Cellule(10, 3, Place(10, 0, 1000, 2000, maitre, partis, arrives)))); var disque = Rendu(10, 0); Color attendu = rouge ? LieuxDeCarte.ROUGE : maitre == JOUEUR ? ReperesDeDepart.COULEUR_JOUEUR : LieuxDeCarte.CouleurDuMaitre(maitre); Assert.That(Disques() == 1 && disque != null && ((Color32)disque.sharedMaterial.color).Equals((Color32)attendu), Is.True, maitre + " " + partis + "/" + arrives); if (partis == 0 && arrives == 0) Assert.That(lieux.TexteLegende.Contains("absent"), Is.False, lieux.TexteLegende);
        }
        [Test] public void LeRougePeutDisparaitre()
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0));
            Material rougeMat = null, maitreMat = null; long tick = 4; FluxDeLieu flux = new FluxDeLieu(0, 7, 2); string cause = null;
            for (int etape = 0; etape < 4; etape++) { if (etape == 1) { flux = new FluxDeLieu(0, 7, 7); tick = 5; } if (etape == 2) { flux = null; cause = "flux non fournis"; tick = 6; } if (etape == 3) { flux = new FluxDeLieu(0, 7, 2); cause = null; tick = 7; } Servir(_ => LectureLieu.De(Cellule(10, tick, new LieuPlace(0, new PointCarte(1000, 2000), JOUEUR, flux, cause, nom: NomDe(10, 0))))); var mat = Rendu(10, 0).sharedMaterial; if (etape == 0) { rougeMat = mat; Assert.That((Color32)mat.color, Is.EqualTo((Color32)LieuxDeCarte.ROUGE)); } if (etape == 1) { maitreMat = mat; Assert.That(mat, Is.Not.SameAs(rougeMat)); Assert.That((Color32)mat.color, Is.EqualTo((Color32)ReperesDeDepart.COULEUR_JOUEUR)); } if (etape == 2) Assert.That(mat == maitreMat && lieux.TexteLegende.Contains("\nAlba : flux non fournis") && lieux.TexteLegende.Contains("relevé au jour 7 de 1400"), Is.True, lieux.TexteLegende); if (etape == 3) Assert.That(mat == rougeMat && !lieux.TexteLegende.Contains("flux non fournis") && lieux.TexteLegende.Contains("relevé au jour 8 de 1400"), Is.True, lieux.TexteLegende); Assert.That(Disques(), Is.EqualTo(1)); }
        }
        [Test] public void LesAbsencesEtLaNavigationRestentHonnetes()
        {
            Preparer(); int n = 0; lieux.Lecteur = _ => { n++; return null; }; lieux.Pas(0); lieux.Pas(3); Assert.That(n == 0 && Disques() == 0, Is.True);
            var porte = new System.Threading.Tasks.TaskCompletionSource<bool>(); lieux.Lecteur = cell => { System.Threading.Interlocked.Increment(ref n); porte.Task.Wait(8000); return Complet(cell, 3); };
            Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(20, 0)); lieux.Pas(0); var fin = DateTime.UtcNow.AddSeconds(5); while (n < 1 && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); lieux.Pas(1); Assert.That(n, Is.EqualTo(1), lieux.TexteLegende);
            Publier("maison-ancienne", new LieuTenu(10, 0), new LieuTenu(20, 0)); porte.TrySetResult(true); fin = DateTime.UtcNow.AddSeconds(5); while (lieux.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); lieux.Pas(1);
            Assert.That(Disques() == 0 && n == 2 && !lieux.LectureEnVol, Is.True, lieux.TexteLegende); horloge = 2; Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); Servir(cell => Complet(cell, 8)); Assert.That(Rendu(10, 0) != null && Rendu(20, 0) != null, Is.True);
            void Reprise(Func<long, LectureLieu> mauvais, Func<bool> bon, string texte) { Servir(mauvais); Assert.That(bon() && lieux.TexteLegende.Contains(texte), Is.True, lieux.TexteLegende); Servir(cell => Complet(cell, 8)); }
            Reprise(cell => cell == 10 ? LectureLieu.Absent("lecture refusée") : Complet(cell, 8), () => Rendu(10, 0) == null && Rendu(10, 1) == null && Rendu(20, 0) != null, "\nTerre sans lieux lus : lecture refusée");
            Reprise(cell => cell == 10 ? LectureLieu.De(Cellule(10, 8)) : Complet(cell, 8), () => Rendu(10, 0) == null && Rendu(20, 0) != null, "\nTerre sans lieux lus : liste vide");
            Reprise(cell => cell == 10 ? LectureLieu.De(new Lieu(10, 8, 1400, 1, 1, new Dictionary<string, double>(), 0, 0, lieux: null, absenceDesLieux: "clé absente : lieux")) : Complet(cell, 8), () => Rendu(10, 0) == null && Rendu(20, 0) != null, "\nTerre sans lieux lus : clé absente : lieux");
            Reprise(cell => cell == 10 ? LectureLieu.De(Cellule(10, 8, Place(10, 0, 1000, 2000, JOUEUR, 1, 2), new LieuPlace(1, null, B, new FluxDeLieu(0, 1, 1), nom: NomDe(10, 1)))) : Complet(cell, 8), () => Rendu(10, 0) != null && Rendu(10, 1) == null && Rendu(20, 0) != null, "\nAlba · Brivas : point absent");
            Reprise(cell => cell == 10 ? LectureLieu.De(Cellule(10, 8, Place(10, 0, 1000, 2000, JOUEUR, 1, 2), new LieuPlace(1, new PointCarte(4000, 2000), null, new FluxDeLieu(0, 1, 1), nom: NomDe(10, 1)))) : Complet(cell, 8), () => Rendu(10, 1) == null && Rendu(10, 0) != null, "\nAlba · Brivas : maître absent");
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
            Func<long, LectureLieu> Lu(double a, FluxDeLieu f20) => cell => LectureLieu.De(cell == 10 ? Cellule(10, 5, new LieuPlace(0, new PointCarte(1, 2), JOUEUR, new FluxDeLieu(1234.4, 0, 0), nom: NomDe(10, 0)), new LieuPlace(1, new PointCarte(30001, 2), JOUEUR, new FluxDeLieu(a, 0, 0), nom: NomDe(10, 1)), new LieuPlace(2, new PointCarte(-29999, 2), B, new FluxDeLieu(90000, 0, 0), nom: NomDe(10, 2)))
                : Cellule(20, 5, new LieuPlace(0, new PointCarte(1, 40002), JOUEUR, f20, f20 == null ? "flux non fournis" : null, nom: NomDe(20, 0))));
            foreach (var (a, b) in new[] { (100000d, 218086d), (25000d, 400000d) })
            {
                Servir(Lu(a, new FluxDeLieu(b, 0, 0))); string t = fleches.TexteLegende; Assert.That(Fleches(), Is.EquivalentTo(new[] { "Flèche 10-1", "Flèche 20-0" }), t); Fleche("10-1", new PointCarte(30001, 2), a); Fleche("20-0", new PointCarte(1, 40002), b);
                Assert.That(t, Does.Contain(FlechesDeCarte.ENTETE).And.Contain("\nSiège : 1,23 t prélevés sur place, sans flèche").And.Contain("\nAlba · Brivas → Siège : " + TexteDuMonde.Masse(a)).And.Contain("\nDara → Siège : " + TexteDuMonde.Masse(b)).And.Not.Contain("10-2").And.Not.Contain("Cerda"));
            }
            Servir(Lu(0, null)); Assert.That(Fleches(), Is.Empty); Assert.That(fleches.TexteLegende, Does.Contain("\nAlba · Brivas → Siège : 0 kg").And.Contain("\nDara → Siège : flux non fournis"));
            Servir(Lu(100000, new FluxDeLieu(1, 0, 0))); Assert.That(Fleches(), Has.Length.EqualTo(2)); Servir(cell => cell == 10 ? LectureLieu.Absent("refus témoin") : LectureLieu.De(new Lieu(20, 5, 1400, 1, 1, new Dictionary<string, double>(), 0, 0, absenceDesLieux: "lieux non servis"))); Assert.That(Fleches(), Is.Empty); Assert.That(fleches.TexteLegende, Does.Contain("\nAucune flèche d'une terre sans lieux lus : refus témoin").And.Contain("\nAucune flèche d'une terre sans lieux lus : lieux non servis").And.Not.Contain("Brivas").And.Not.Contain("Dara"));
            Servir(Lu(100000, new FluxDeLieu(1, 0, 0))); Assert.That(Fleches(), Has.Length.EqualTo(2)); Publier(C, new LieuTenu(10, 0)); lieux.Pas(horloge); Assert.That(Fleches(), Is.Empty); Assert.That(fleches.TexteLegende, Does.Not.Contain("Brivas"));
        }
        [Test] public void LeDuPartVersLeSiegeDuSuzerain()
        {
            Preparer(); fleches = racine.GetComponent<FlechesDeCarte>(); int n = 0; fleches.Lecteur = _ => { n++; return null; }; fleches.Pas(0); Assert.That(n == 0 && !fleches.LectureEnVol, Is.True); Publier(JOUEUR, new LieuTenu(10, 0));
            MaisonLue M(string id, PointCarte? p, string raison = null) => new MaisonLue(id, id, new SiegeDeMaison(p == null ? (long?)null : 30, p == null ? (long?)null : 0, id == JOUEUR ? "Siège" : "Capitale", p), new LieuTenu[0], raison == null ? new Dictionary<string, string>() : new Dictionary<string, string> { ["siege"] = raison });
            Lecture<ComptesDeMaison> Comptes(string id, PointCarte? p, string suzerain, string raison = null) => Lecture<ComptesDeMaison>.De(new ComptesDeMaison(M(id, p, raison), suzerain, 0.6, null, new FluxDeMaison(999999, 0, id == JOUEUR ? 76788.18 : 5, 0, 0, 0, 0, null)));
            PointCarte haut = new PointCarte(60001, 50002), siege = new PointCarte(1, 2); Func<string, Lecture<ComptesDeMaison>> bon = id => id == JOUEUR ? Comptes(JOUEUR, siege, B) : Comptes(B, haut, null);
            var etapes = new (Func<string, Lecture<ComptesDeMaison>>, string)[] { (bon, "\nSiège → Capitale : 76,8 t de dû"), (_ => Comptes(JOUEUR, siege, null), "\nDû au suzerain : sans suzerain : aucun dû"),
                (id => id == JOUEUR ? Comptes(JOUEUR, siege, B) : Comptes(B, null, null, "siège non servi"), "\nDû au suzerain : siège du suzerain hors carte : siège non servi"), (_ => Lecture<ComptesDeMaison>.Absent("refus témoin"), "\nDû au suzerain : lecture refusée : refus témoin"), (bon, "Capitale : ") };
            foreach (var (lire, texte) in etapes) { Du(lire); bool vue = lire == bon; Assert.That(fleches.TexteLegende, Does.Contain(texte)); Assert.That(Fleches(), Is.EqualTo(vue ? new[] { FlechesDeCarte.DU } : new string[0]), texte); if (vue) Fleche("du dû", siege, 76788.18, haut); }
            var porte = new System.Threading.Tasks.TaskCompletionSource<Lecture<ComptesDeMaison>>(); Du(_ => Comptes(JOUEUR, siege, null)); fleches.Lecteur = id => id == JOUEUR ? porte.Task.Result : bon(id); fleches.Pas(horloge); Assert.That(fleches.LectureEnVol, Is.True);
            Publier(C, new LieuTenu(10, 0)); fleches.Pas(horloge); porte.SetResult(Comptes(JOUEUR, siege, B)); var fin = DateTime.UtcNow.AddSeconds(5); while (fleches.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); fleches.Pas(horloge);
            Assert.That(Fleches(), Is.Empty); Assert.That(fleches.TexteLegende, Does.Not.Contain("de dû"));
        }
        // Lot #875 : les deux légendes nomment chaque terre par son bourg, chaque lieu par son nom servi, et pèsent en tonnes.
        const string ABSENT = "TexteDuMonde : absence déclarée par le monde : ";
        [Test] public void La_legende_des_lieux_nomme_date_et_declare_l_absent()
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(10, 2), new LieuTenu(20, 0), new LieuTenu(30, 0));
            LogAssert.Expect(LogType.Log, ABSENT + "nom absent pour 10-0"); LogAssert.Expect(LogType.Log, ABSENT + "flux absents au tick 4"); LogAssert.Expect(LogType.Log, ABSENT + "lieu 30 : délai dépassé");
            Servir(cell => cell == 30 ? LectureLieu.Absent("lieu 30 : délai dépassé") : LectureLieu.De(cell == 20 ? Cellule(20, 4, Place(20, 0, 8000, 3000, B, 1, 1))
                : Cellule(10, 4, new LieuPlace(0, new PointCarte(1000, 2000), JOUEUR, new FluxDeLieu(0, 1, 1), absenceDuNom: "nom absent pour 10-0"), new LieuPlace(1, new PointCarte(4000, 2000), JOUEUR, null, "flux absents au tick 4", nom: "Brivas"), new LieuPlace(2, null, JOUEUR, new FluxDeLieu(0, 1, 1)))));
            string t = lieux.TexteLegende; const string SANS = "\nBourg sans nom (déclaré absent par le monde)";
            Assert.That(t, Does.Contain(SANS + " · relevé au jour 5 de 1400").And.Contain(SANS + " · Brivas : déclaré absent par le monde").And.Contain(SANS + " · lieu sans nom (nom non fourni) : point absent").And.Contain("\nDara · relevé au jour 5 de 1400").And.Contain("\nTerre sans lieux lus : déclaré absent par le monde"));
            Assert.That(TexteDuMonde.Interdit(t, JOUEUR, B, C) ?? TexteDuMonde.SansUnite(t), Is.Null, t); Assert.That(racine.transform.Find(LieuxDeCarte.RACINE + "/Lieu 10-1"), Is.Not.Null);
        }
        [Test] public void La_legende_des_fleches_nomme_et_pese()
        {
            Preparer(); fleches = racine.GetComponent<FlechesDeCarte>(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(10, 2)); const string HAUT = "grande-15";
            void Propre(string etape) { string t = fleches.TexteLegende; Assert.That(TexteDuMonde.Interdit(t, JOUEUR, B, C, HAUT) ?? TexteDuMonde.SansUnite(t), Is.Null, etape + " : " + t); Assert.That(Fleches(), Does.Contain("Flèche 10-1").And.Contain("Flèche 10-2"), etape); }
            Servir(_ => LectureLieu.De(Cellule(10, 4, new LieuPlace(0, new PointCarte(1, 2), JOUEUR, new FluxDeLieu(1234.4, 0, 0), nom: "Alba"), new LieuPlace(1, new PointCarte(30001, 2), JOUEUR, new FluxDeLieu(570982.18, 0, 0), nom: "Brivas"), new LieuPlace(2, new PointCarte(-29999, 2), JOUEUR, new FluxDeLieu(90000, 0, 0)))));
            Assert.That(fleches.TexteLegende, Does.Contain("\nSiège : 1,23 t prélevés sur place, sans flèche").And.Contain("\nAlba · Brivas → Siège : 571 t").And.Contain("\nAlba · lieu sans nom (nom non fourni) → Siège : 90,0 t")); Propre("lieux");
            MaisonLue M(string id, PointCarte p) => new MaisonLue(id, id, new SiegeDeMaison(30, 0, id == JOUEUR ? "Siège" : "Capitale", p), new LieuTenu[0], new Dictionary<string, string>());
            Lecture<ComptesDeMaison> Comptes(string id, PointCarte p, string suzerain) => Lecture<ComptesDeMaison>.De(new ComptesDeMaison(M(id, p), suzerain, 0.6, null, new FluxDeMaison(999999, 0, id == JOUEUR ? 76788.18 : 5, 0, 0, 0, 0, null)));
            Du(id => id == JOUEUR ? Comptes(JOUEUR, new PointCarte(1, 2), HAUT) : Comptes(HAUT, new PointCarte(60001, 50002), null)); Assert.That(fleches.TexteLegende, Does.Contain("\nSiège → Capitale : 76,8 t de dû")); Propre("dû");
            LogAssert.Expect(LogType.Log, ABSENT + "maison grande-15 : délai dépassé");
            Du(id => id == JOUEUR ? Comptes(JOUEUR, new PointCarte(1, 2), HAUT) : Lecture<ComptesDeMaison>.Absent("maison grande-15 : délai dépassé")); Assert.That(fleches.TexteLegende, Does.Contain("\nDû au suzerain : suzerain non lu : déclaré absent par le monde")); Propre("suzerain");
        }
        // Lot #964 : plus de légende flottante ; les lieux parlent dans la légende des Puissances, les flèches dans celle du Flux, leurs relevés dans l'infobulle.
        static readonly string[] FLOTTANTES = { "Légende des lieux", "Fond de la légende", "Légende des flèches", "Fond des flèches" };
        string Flottante() => racine.transform.Find("Cabinet").GetComponentsInChildren<Transform>(true).Select(t => t.name).FirstOrDefault(FLOTTANTES.Contains);
        string Legende(CalquesCarte calques, string texte, string detail) { Assert.DoesNotThrow(() => calques.Legender(texte, detail)); foreach (float echelle in new[] { 1f, 2f / 3f }) Assert.That(CalquesCarte.Lignes(calques.Legende, texte, echelle), Is.InRange(1, CalquesCarte.LIGNES_MAX), "échelle " + echelle);
            string bulle = racine.transform.Find("Cabinet/" + CalquesCarte.LEGENDE).GetComponent<Infobulle>().Phrase; Assert.That(bulle, Is.EqualTo(texte + "\n" + detail)); Assert.That(TexteDuMonde.Interdit(bulle, JOUEUR, B, C) ?? TexteDuMonde.SansUnite(bulle), Is.Null, bulle); return bulle; }
        [Test] public void Les_lieux_parlent_dans_la_legende_des_Puissances()
        {
            Preparer(); fleches = racine.GetComponent<FlechesDeCarte>(); var calques = racine.GetComponent<CalquesCarte>(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); Servir(cell => Reponse(cell, 4, false)); Assert.That(Flottante(), Is.Null); Assert.That(lieux.Peint, Is.True);
            string legende = CalquesCarte.LegendeDuMode(ModeDeCarte.Puissances, null, true), detail = CalquesCarte.DetailDuMode(ModeDeCarte.Puissances, lieux, fleches); Assert.That(legende, Is.EqualTo(CalquesCarte.PUISSANCES + "\n" + LieuxDeCarte.ENTETE));
            Assert.That(detail, Is.EqualTo(CalquesCarte.DetailDuMode(ModeDeCarte.Puissances) + " Relief non transmis." + lieux.TexteLegende.Substring(LieuxDeCarte.ENTETE.Length)).And.Contain("\nAlba · relevé au jour 5 de 1400").And.Contain("\nDara · relevé au jour 5 de 1400"));
            string bulle = Legende(calques, legende, detail); Assert.That(bulle.Split(new[] { LieuxDeCarte.ENTETE }, StringSplitOptions.None).Length, Is.EqualTo(2), "l'en-tête des lieux une seule fois : " + bulle);
            Assert.That(CalquesCarte.LegendeDuMode(ModeDeCarte.Puissances, null, false), Is.EqualTo(CalquesCarte.LegendeDuCalque(null)), "contre-épreuve : sans lieux peints"); Assert.That(CalquesCarte.DetailDuMode(ModeDeCarte.Puissances, null, null), Is.EqualTo(CalquesCarte.DetailDuMode(ModeDeCarte.Puissances)), "contre-épreuve : sans vue des lieux");
            Assert.Throws<ArgumentException>(() => calques.Legender(CalquesCarte.PUISSANCES + "\n" + FlechesDeCarte.ENTETE, detail), "contre-épreuve : l'en-tête des flèches ne tient pas dans la légende");
        }
        [Test] public void Les_fleches_ne_se_montrent_qu_en_mode_Flux()
        {
            Preparer(); fleches = racine.GetComponent<FlechesDeCarte>(); var calques = racine.GetComponent<CalquesCarte>(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); const double a = 100000, b = 218086;
            fleches.Lecteur = _ => Lecture<ComptesDeMaison>.De(new ComptesDeMaison(new MaisonLue(JOUEUR, "Maison", new SiegeDeMaison(10, 0, "Siège", new PointCarte(1, 2)), new LieuTenu[0], new Dictionary<string, string>()), null, 0.6, null, new FluxDeMaison(0, 0, 0, 0, 0, 0, 0, null)));
            Servir(cell => LectureLieu.De(cell == 10 ? Cellule(10, 5, new LieuPlace(0, new PointCarte(1, 2), JOUEUR, new FluxDeLieu(1234.4, 0, 0), nom: NomDe(10, 0)), new LieuPlace(1, new PointCarte(30001, 2), JOUEUR, new FluxDeLieu(a, 0, 0), nom: NomDe(10, 1)), new LieuPlace(2, new PointCarte(-29999, 2), B, new FluxDeLieu(90000, 0, 0), nom: NomDe(10, 2)))
                : Cellule(20, 5, new LieuPlace(0, new PointCarte(1, 40002), JOUEUR, new FluxDeLieu(b, 0, 0), nom: NomDe(20, 0)))));
            var noms = new[] { "Flèche 10-1", "Flèche 20-0" }; var tige = racine.transform.Find(FlechesDeCarte.RACINE); Transform bande = racine.transform.Find("Cabinet/" + CalquesCarte.BANDE); Assert.That(Fleches(), Is.EquivalentTo(noms)); Assert.That(tige.gameObject.activeSelf, Is.False, "le cabinet s'ouvre en Puissances : flèches cachées");
            foreach (var (mode, visibles) in new[] { (ModeDeCarte.Flux, true), (ModeDeCarte.Habitants, false), (ModeDeCarte.Puissances, false), (ModeDeCarte.Flux, true) }) { bande.Find(mode.ToString()).GetComponent<Button>().onClick.Invoke(); fleches.Pas(horloge); Assert.That(tige.gameObject.activeSelf, Is.EqualTo(visibles), mode.ToString()); Assert.That(Fleches(), Is.EquivalentTo(noms), mode.ToString()); }
            Assert.That(Flottante(), Is.Null); string detail = CalquesCarte.DetailDuMode(ModeDeCarte.Flux, lieux, fleches); Legende(calques, CalquesCarte.FLUX, detail);
            Assert.That(detail, Is.EqualTo(CalquesCarte.DetailDuMode(ModeDeCarte.Flux) + "\n" + fleches.TexteLegende).And.Contain(FlechesDeCarte.ENTETE).And.Contain("\nAlba · Brivas → Siège : " + TexteDuMonde.Masse(100000)));
            Assert.Throws<ArgumentException>(() => calques.Legender(FlechesDeCarte.ENTETE + " · Rouge : territoire conservé", detail), "contre-épreuve : l'en-tête entier des flèches ne tient pas dans la légende");
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
        static LectureLieu Reponse(long cell, long tick, bool inverse) { var tous = Attendu().Where(p => p.Item1 == cell).Select(p => Place(cell, p.Item2, p.Item3, p.Item4, p.Item5, 1, 2)).ToArray(); if (inverse) Array.Reverse(tous); return LectureLieu.De(Cellule(cell, tick, tous)); }
        static LectureLieu Complet(long cell, long tick) => cell == 20 ? LectureLieu.De(Cellule(20, tick, Place(20, 0, 8000, 3000, JOUEUR, 0, 1))) : cell == 10 ? LectureLieu.De(Cellule(10, tick, Place(10, 0, 1000, 2000, JOUEUR, 1, 2), Place(10, 1, 4000, 2000, B, 1, 1))) : LectureLieu.Absent("cellule extérieure " + cell);
        static Lieu Cellule(long cell, long tick, params LieuPlace[] places) => new Lieu(cell, tick, 1400, (int)tick + 1, 1, new Dictionary<string, double>(), 0, 0, lieux: places); // le service sert le jour tick + 1
        static LieuPlace Place(long cell, long rang, double x, double y, string maitre, long partis, long arrives) => new LieuPlace(rang, new PointCarte(x, y), maitre, new FluxDeLieu(0, partis, arrives), nom: NomDe(cell, rang));
        static string NomDe(long cell, long rang) => (cell, rang) switch { (10, 0) => "Alba", (10, 1) => "Brivas", (10, 2) => "Cerda", (20, 0) => "Dara", (20, 1) => "Elne", _ => throw new ArgumentOutOfRangeException(nameof(rang), "aucun nom pour " + cell + "-" + rang) };
        MeshRenderer Rendu(long cell, long rang) { var t = racine.transform.Find(LieuxDeCarte.RACINE + "/" + ReperesDeDepart.NomDuLieu(cell, rang) + "/Disque"); return t != null && t.gameObject.activeInHierarchy ? t.GetComponent<MeshRenderer>() : null; }
        int Disques() { var r = racine.transform.Find(LieuxDeCarte.RACINE); if (r == null) return 0; int n = 0; foreach (Transform e in r) { var d = e.Find("Disque"); if (d != null && d.gameObject.activeInHierarchy) n++; } return n; }
        // Lot #855 : un clic gauche court garde la terre, un glisser ne choisit rien, Échap ferme le dossier avant d'ouvrir le menu.
        static readonly Vector2 O = new Vector2(400, 300);
        static CelluleDeCarte Terre(long id, string ville) => new CelluleDeCarte(id, new PolygoneDeCarte[0], new IdentiteDeCarte(1, "Puissance test"), null, new[] { new VilleDeCarte(ville, 12, new PointCarte(0, 0)) });
        MeshRenderer Teinte(long id) { var r = new GameObject("Cellule " + id).AddComponent<MeshRenderer>(); r.transform.SetParent(racine.transform, false); return r; }
        bool Geste(CelluleDeCarte sous, params Vector2[] chemin) { bool garde = cabinet.Noter(chemin[0], true, false, false, sous); for (int i = 1; i < chemin.Length; i++) garde |= cabinet.Noter(chemin[i], false, i == chemin.Length - 1, false, sous); return garde; }
        string Territoire() => racine.GetComponentsInChildren<Text>(true).Single(t => t.transform.parent.name == "Lecture du territoire").text;
        [Test] public void UnClicSansMouvementGardeLaTerre()
        {
            var teinte = Teinte(7); var sept = Terre(7, "Ville test");
            Assert.That(Geste(sept, O, O), Is.True); Assert.That(cabinet.Retenue, Is.SameAs(sept)); cabinet.Afficher(); Assert.That(Territoire(), Does.Contain("Ville test"));
            cabinet.Relacher(); Assert.That(cabinet.Noter(O, true, true, false, sept) && cabinet.Retenue == sept, Is.True, "appui et relâché dans la même image");
            cabinet.Relacher(); Assert.That(Geste(sept, O, O + new Vector2(6, 0)) && cabinet.Retenue == sept, Is.True, "relâché à 6 px");
            Assert.That(teinte.HasPropertyBlock(), Is.True);
        }
        [Test] public void UnGlisserNeChangePasLaTerreGardee()
        {
            var sept = Terre(7, "Ville test"); var neuf = Terre(9, "Ville neuve"); Assert.That(Geste(sept, O, O), Is.True);
            foreach (var chemin in new[] { new[] { O, O + new Vector2(40, 0), O + new Vector2(40, 0) }, new[] { O, O + new Vector2(100, 0), O }, new[] { O, O + new Vector2(7, 0) } })
                Assert.That(!Geste(neuf, chemin) && cabinet.Retenue == sept, Is.True, "glisser par " + string.Join(" → ", chemin.Select(p => p.ToString())));
        }
        [Test] public void UnClicSurUnPanneauNeTraversePas()
        {
            var sept = Terre(7, "Ville test");
            Assert.That(cabinet.Noter(O, true, false, true, sept) | cabinet.Noter(O, false, true, false, sept), Is.False, "appui sur un panneau");
            Assert.That(cabinet.Noter(O, true, false, false, sept) | cabinet.Noter(O, false, true, true, sept), Is.False, "relâché sur un panneau");
            Assert.That(cabinet.Noter(O, false, true, false, sept), Is.False, "relâché sans appui");
            Assert.That(cabinet.Retenue, Is.Null); Assert.That(cabinet.HorsCarte(O), Is.True, "sans caméra, tout est hors de la carte");
        }
        [Test] public void EchapFermeLeDossierAvantDOuvrirLeMenu()
        {
            var teinte = Teinte(7); var menu = racine.GetComponent<MenuCabinet>(); Assert.That(Geste(Terre(7, "Ville test"), O, O) && !menu.Ouvert, Is.True); cabinet.Afficher();
            menu.Echap(); cabinet.Afficher();
            Assert.That(cabinet.Retenue == null && !menu.Ouvert && !teinte.HasPropertyBlock(), Is.True, "le premier Échap ferme le dossier, pas plus");
            Assert.That(Territoire(), Does.Contain("Clic gauche sur une terre pour ouvrir son dossier.").And.Not.Contain("Ville test"));
            menu.Echap(); Assert.That(menu.Ouvert, Is.True); menu.Echap(); Assert.That(menu.Ouvert, Is.False);
            menu.Echap(); Assert.That(menu.Ouvert, Is.True, "sans terre gardée, Échap ouvre le menu"); menu.Fermer();
        }
        [Test] public void LesAidesDisentLesNouveauxGestes()
        {
            Assert.That(CabinetDeCarte.AIDE, Does.Contain("Clic").And.Contain("Glisser").And.Contain("Échap").And.Not.Contain("Clic droit").And.Not.Contain("\n"));
            Assert.That(racine.GetComponentsInChildren<Text>(true).Where(t => t.text == CabinetDeCarte.AIDE).Select(t => t.name), Is.Empty, "l'aide s'écrit encore seule dans un texte");
            Canvas toile = racine.transform.Find("Cabinet").GetComponent<Canvas>(); Canvas.ForceUpdateCanvases(); var bouton = (RectTransform)toile.transform.Find("Menu"); string phrase = bouton.GetComponent<Infobulle>().Phrase;
            Assert.That(phrase, Does.StartWith("Ouvre ou ferme le menu").And.EndWith("\n" + CabinetDeCarte.AIDE));
            var coins = new Vector3[4]; bouton.GetWorldCorners(coins); RectTransform feuillet = Infobulle.Montrer(toile, phrase, RectTransformUtility.WorldToScreenPoint(null, (coins[0] + coins[2]) / 2)); Text ecrit = feuillet.GetComponentInChildren<Text>();
            Assert.That(ecrit.text, Is.EqualTo(phrase)); Assert.That(ecrit.preferredHeight, Is.LessThanOrEqualTo(ecrit.rectTransform.rect.height + .5f), "la phrase du Menu déborde de son infobulle");
            Vector2 p = new Vector2(260, 692); Rect rendu = Infobulle.Placer(p, feuillet.sizeDelta * 2f / 3f, new Vector2(1280, 720)); // le centre du Menu en 1280 × 720
            Assert.That(rendu.xMin >= 0 && rendu.yMin >= 0 && rendu.xMax <= 1280 && rendu.yMax <= 720 && !rendu.Contains(p), Is.True, "infobulle du Menu " + rendu + " en 1280 × 720");
            var menu = racine.GetComponentsInChildren<Text>(true).Single(t => t.transform.parent.name == "Menu du cabinet" && t.rectTransform.sizeDelta.y == 410f);
            Assert.That(menu.text, Does.Contain("Clic gauche").And.Contain("Double-clic").And.Contain("Échap").And.Not.Contain("Clic droit"));
            Assert.That(menu.preferredHeight, Is.LessThanOrEqualTo(menu.rectTransform.rect.height));
            Assert.That(System.IO.File.ReadAllText("Assets/Interface/CabinetDeCarte.cs"), Does.Not.Contain("rightButton").And.Not.Contain("PassageALaCapitale"));
            var survol = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("ForgeLocal3D.SurvolDeCarte")).First(t => t != null);
            Assert.That(CabinetDeCarte.SEUIL_CLIC_PX, Is.EqualTo((float)survol.GetField("SEUIL_CLIC_PX").GetValue(null)));
        }
        // Lot #873 : « Votre maison » parle en noms et en dates ; le tick ne va qu'au journal.
        const string APERCU = "Consultez une maison avant de vous engager."; Text Nomme(string nom) => racine.GetComponentsInChildren<Text>(true).Single(t => t.name == nom);
        string Propre(string nom) { string t = Nomme(nom).text; Assert.That(TexteDuMonde.Interdit(t, "10340") ?? TexteDuMonde.SansUnite(t), Is.Null, t); return t; }
        [Test] public void LaMaisonDuJoueurDitSonNomSonSiegeSesLieuxEtLaDate()
        {
            Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); cabinet.Afficher(); Assert.That(Propre("Lecture de la partie…"), Is.EqualTo("Maison\nSiège : Siège\n3 lieux tenus · relevé au jour 1 de 1400"));
            Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); Assert.That(Propre("Lecture de la partie…"), Does.EndWith("\n1 lieu tenu · relevé au jour 1 de 1400"));
        }
        void Proposer()
        {
            partie = new LecturePartie(() => null, _ => null, () => null, _ => null); cabinet.Partie = partie; Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(1, new DateDuMonde(1400, 1), 0, new CelluleDuMonde[0]), null)));
            Poser(partie, "Departs", Lecture<DepartsLus>.De(new DepartsLus(1, new DateDuMonde(1400, 1), new[] { new FicheDeDepart(42, "Despotat témoin", "Maison témoin", new SiegeDeDepart("Mistra", 0, 0), 10340, 12345, null, new VoisinDeDepart[0]) })));
            cabinet.Afficher(); racine.GetComponentsInChildren<Button>(true).Single(b => b.name == "Maison témoin").onClick.Invoke(); cabinet.Afficher();
        }
        [Test] public void LApercuDuChoixDitLesHabitantsAutourDuSiege()
        {
            Proposer(); Assert.That(Propre(APERCU), Is.EqualTo("Despotat témoin · Mistra\n12 345 habitants autour de Mistra\nSuzerain : aucun")); Assert.That(TexteDuMonde.Interdit(Nomme(APERCU).text, "10340", "42"), Is.Null);
        }
        [Test] public void LeRecuNEstDateQuAuTickDeLHorloge()
        {
            Proposer(); Poser(partie, "Recu", RecuIntention.AccepteeAu(7)); LogAssert.Expect(LogType.Log, "CabinetDeCarte : choix reçu au tick 7");
            string Lu(HorlogeLue lue) { Poser(racine.GetComponent<HorlogeDeCarte>(), "Lue", lue); cabinet.Afficher(); Assert.That(Nomme(APERCU).text, Does.Not.Contain("tick 7")); return Propre(APERCU); }
            Assert.That(Lu(null), Is.EqualTo("Choix reçu ; le monde l'applique au jour suivant."));
            Assert.That(Lu(new HorlogeLue(7, new DateDuMonde(1400, 8), 0)), Is.EqualTo("Choix reçu le jour 8 de 1400.\nReprenez le temps : le monde l'appliquera au jour suivant."));
            Assert.That(Lu(new HorlogeLue(8, new DateDuMonde(1400, 9), 0)), Is.EqualTo("Choix reçu ; le monde l'applique au jour suivant.").And.Not.Contain("jour 9").And.Not.Contain("jour 8"));
            Poser(partie, "Recu", RecuIntention.Refusee(409, "maison 10340 déjà prise")); Assert.That(Lu(null), Is.EqualTo("Demande refusée : déclaré absent par le monde"));
            Poser(partie, "Recu", RecuIntention.Absente("service coupé")); Assert.That(Lu(null), Is.EqualTo("Envoi non confirmé : service coupé"));
        }
        // Lot #879 : chaque commande du cabinet déclare sa phrase, et le cabinet la montre au survol.
        [Test] public void ChaqueCommandeDuCabinetDitCeQuElleFait()
        {
            Proposer(); Transform toile = racine.transform.Find("Cabinet"); Button[] boutons = toile.GetComponentsInChildren<Button>(true);
            var attendues = new[] { "Ralentir", "Pause / Reprendre", "Accélérer", "Choisir cette maison", "Maison témoin", "Prélèvement", "Ouvrir le grenier", "Préparer", "Confirmer l’ordre",
                "Annuler / Retour", "Annuler / Retour", "Menu", "Revenir au jeu", "Puissances", "Habitants", "Autres maisons", "Plan du bourg", "Revenir à la carte", "Chantiers",
                "Tracer une rue", "Relire le tracé", "Confirmer la rue", "Terres et comptes", "Fermer", "Fermer", "Fermer" };
            Assert.That(attendues.Length == 26 && attendues.Distinct().Count() == 23, Is.True);
            foreach (var nom in attendues.GroupBy(n => n)) Assert.That(boutons.Count(b => b.name == nom.Key), Is.GreaterThanOrEqualTo(nom.Count()), "commande absente du cabinet : " + nom.Key);
            Assert.That(boutons.Length, Is.GreaterThanOrEqualTo(26));
            string[] sans = CabinetDeCarte.CommandesSansPhrase(toile); Assert.That(sans, Is.Empty, "commandes sans phrase : " + string.Join(", ", sans));
            Assert.That(boutons.Single(b => b.name == "Confirmer l’ordre").GetComponent<Infobulle>().Phrase, Is.EqualTo("Envoie l'ordre préparé au monde ; il l'applique au jour suivant."));
            SocleInterface.Commande(toile, "Témoin sans phrase", 0, 0, null); Assert.That(CabinetDeCarte.CommandesSansPhrase(toile), Is.EqualTo(new[] { "Témoin sans phrase" }));
            SocleInterface.Commande(toile, "Témoin muet", 0, 0, null, true, "Témoin muet"); Assert.That(CabinetDeCarte.CommandesSansPhrase(toile), Is.EqualTo(new[] { "Témoin sans phrase", "Témoin muet" }));
            var vide = new GameObject("Toile vide"); try { Assert.Throws<ArgumentException>(() => CabinetDeCarte.CommandesSansPhrase(vide.transform)); } finally { Object.DestroyImmediate(vide); }
        }
        [Test] public void LeCabinetMontreLaPhraseDuBoutonSurvole()
        {
            Proposer(); Transform toile = racine.transform.Find("Cabinet"); Canvas canvas = toile.GetComponent<Canvas>(); Canvas.ForceUpdateCanvases(); // la toile prend l'écran, comme dans SocleInterfaceTests
            Button[] actifs = toile.GetComponentsInChildren<Button>().Where(b => b.gameObject.activeInHierarchy).ToArray(); var coins = new Vector3[4];
            foreach (var nom in new[] { "Ralentir", "Pause / Reprendre", "Accélérer", "Menu", "Terres et comptes", "Maison témoin", "Choisir cette maison", "Plan du bourg", "Puissances", "Habitants", "Autres maisons" })
                Assert.That(actifs.Any(b => b.name == nom), Is.True, "commande active absente : " + nom);
            RectTransform[] Feuillets() => toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray();
            Vector2 Centre(Button b) { ((RectTransform)b.transform).GetWorldCorners(coins); return RectTransformUtility.WorldToScreenPoint(null, (coins[0] + coins[2]) / 2); }
            void Survoler(Button b, Vector2 point) => UnityEngine.EventSystems.ExecuteEvents.Execute(b.gameObject, new UnityEngine.EventSystems.PointerEventData(null) { position = point }, UnityEngine.EventSystems.ExecuteEvents.pointerEnterHandler);
            foreach (var bouton in actifs)
            {
                Vector2 point = Centre(bouton); Survoler(bouton, point); RectTransform[] feuillets = Feuillets();
                Assert.That(feuillets.Length, Is.EqualTo(1), bouton.name + " ne montre pas un seul feuillet");
                Assert.That(feuillets[0].GetComponentInChildren<Text>().text, Is.EqualTo(bouton.GetComponent<Infobulle>().Phrase), bouton.name);
                feuillets[0].GetWorldCorners(coins); Rect ecran = canvas.pixelRect;
                foreach (var c in coins.Select(c => RectTransformUtility.WorldToScreenPoint(null, c)))
                    Assert.That(c.x >= ecran.xMin - .5f && c.x <= ecran.xMax + .5f && c.y >= ecran.yMin - .5f && c.y <= ecran.yMax + .5f, Is.True, bouton.name + " : coin " + c + " hors de " + ecran);
                UnityEngine.EventSystems.ExecuteEvents.Execute(bouton.gameObject, new UnityEngine.EventSystems.PointerEventData(null) { position = point }, UnityEngine.EventSystems.ExecuteEvents.pointerExitHandler);
                Assert.That(Feuillets(), Is.Empty, bouton.name + " : le feuillet reste après la sortie");
            }
            Assert.That(racine.GetComponentsInChildren<Canvas>(true).Length, Is.EqualTo(1));
            Assert.That(toile.Find("Infobulle").GetComponentsInChildren<Graphic>(true).Where(g => g.raycastTarget).Select(g => g.name), Is.Empty);
            Button muet = actifs.Single(b => b.name == "Menu"); Object.DestroyImmediate(muet.GetComponent<Infobulle>());
            Survoler(muet, Centre(muet)); Assert.That(Feuillets(), Is.Empty, "un bouton sans Infobulle montre un feuillet");
        }
        // Lot #880 : l'infobulle d'une terre dit les trois premières lignes de sa fiche, et n'efface pas la phrase d'un bouton.
        static DocumentDuMonde DocTerre(long cell, string nom, int tick = 8, int jour = 9) => new DocumentDuMonde("{\"tick\":" + tick + ",\"cell_id\":" + cell + ",\"date\":{\"annee\":1400,\"jour_de_l_annee\":" + jour + "},\"population\":12345,\"noms\":{\"maisons\":{\"m-1\":{\"nom\":\"Maison témoin\"}}},\"lieux\":[{\"rang\":0,\"nom\":\"" + nom + "\",\"population\":12000,\"surface_km2\":12,\"maitre\":\"m-1\",\"stocks\":{\"nourriture\":1234.5},\"flux_30j\":null}]}");
        static async System.Threading.Tasks.Task Fin(LectureDossier lecture) { for (int i = 0; i < 40 && lecture.EnCours; i++) await System.Threading.Tasks.Task.Yield(); Assert.That(lecture.EnCours, Is.False, lecture.Cle); }
        async System.Threading.Tasks.Task<(InfobulleDeTerre bulle, CelluleDeCarte terre)> Montrer20()
        {
            var bulle = racine.GetComponent<InfobulleDeTerre>(); bulle.automatique = true; var terre = Terre(20, "Bourg témoin");
            var porte = new System.Threading.Tasks.TaskCompletionSource<DocumentDuMonde>(); bulle.Lecture = new LectureDossier(_ => porte.Task);
            bulle.Pas(O, terre, 0); porte.SetResult(DocTerre(20, "Bourg témoin")); await Fin(bulle.Lecture); bulle.Pas(O, terre, 0.5);
            Assert.That(bulle.TexteAffiche, Does.StartWith("Bourg témoin · ")); return (bulle, terre);
        }
        [Test] public async System.Threading.Tasks.Task LInfobulleDUneTerreDitLesLignesDeSaFiche()
        {
            Assert.That(racine.GetComponents<InfobulleDeTerre>(), Has.Length.EqualTo(1)); cabinet.Construire(); Assert.That(racine.GetComponents<InfobulleDeTerre>(), Has.Length.EqualTo(1));
            var bulle = racine.GetComponent<InfobulleDeTerre>(); bulle.automatique = true; var chemins = new System.Collections.Generic.List<string>(); var portes = new System.Collections.Generic.List<System.Threading.Tasks.TaskCompletionSource<DocumentDuMonde>>();
            bulle.Lecture = new LectureDossier(chemin => { chemins.Add(chemin); var porte = new System.Threading.Tasks.TaskCompletionSource<DocumentDuMonde>(); portes.Add(porte); return porte.Task; });
            var t10 = Terre(10, "Bourg dix"); var t20 = Terre(20, "Bourg témoin"); bulle.Pas(O, t10, 0);
            Assert.That(chemins, Is.EqualTo(new[] { "/lieu?cell=10" })); Assert.That(bulle.TexteAffiche, Is.EqualTo(DossierTerritoire.ATTENTE));
            bulle.Pas(O, t20, 0.1); Assert.That(chemins, Has.Count.EqualTo(1)); Assert.That(bulle.TexteAffiche, Is.EqualTo(DossierTerritoire.ATTENTE));
            portes[0].SetResult(DocTerre(10, "Bourg dix")); await Fin(bulle.Lecture); bulle.Pas(O, t20, 0.2);
            Assert.That(chemins, Is.EqualTo(new[] { "/lieu?cell=10", "/lieu?cell=20" })); Assert.That(bulle.TexteAffiche, Is.EqualTo(DossierTerritoire.ATTENTE)); Assert.That(bulle.TexteAffiche, Does.Not.Contain("Bourg dix").And.Not.Contain("Dossier incomplet"));
            var doc20 = DocTerre(20, "Bourg témoin"); portes[1].SetResult(doc20); await Fin(bulle.Lecture); bulle.Pas(O, t20, 0.5);
            string attendu = "Bourg témoin · Maison : Maison témoin\njour 9 de 1400\n" + TexteDuMonde.Nombre(12345) + " habitants dans le territoire"; string dossier = DossierTerritoire.Texte(null, doc20, 20);
            Assert.That(bulle.TexteAffiche, Is.EqualTo(attendu)); Assert.That(bulle.TexteAffiche.Split('\n'), Is.EqualTo(dossier.Split('\n').Take(InfobulleDeTerre.LIGNES).ToArray()));
            var toile = racine.transform.Find("Cabinet"); var feuillets = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray();
            Assert.That(feuillets.Length, Is.EqualTo(1)); Assert.That(feuillets[0].GetComponentInChildren<Text>().text, Is.EqualTo(attendu));
            int n = chemins.Count; bulle.Pas(O, t20, 1); Assert.That(chemins, Has.Count.EqualTo(n)); bulle.Pas(O, t20, 2.3); Assert.That(chemins, Is.EqualTo(new[] { "/lieu?cell=10", "/lieu?cell=20", "/lieu?cell=20" }));
            string ligne = InfobulleDeTerre.Decrire(null, DocTerre(20, "Bourg témoin", 9, 10), 20).Split('\n')[1]; Assert.That(ligne, Is.EqualTo("jour 10 de 1400")); Assert.That(ligne, Is.Not.EqualTo(dossier.Split('\n')[1]));
        }
        [Test] public async System.Threading.Tasks.Task LInfobulleDeLaTerreLaisseLaPhraseDUnBouton()
        {
            var (bulle, terre) = await Montrer20(); Transform toile = racine.transform.Find("Cabinet"); Canvas.ForceUpdateCanvases();
            Button bouton = toile.GetComponentsInChildren<Button>().Single(b => b.name == "Pause / Reprendre"); var coins = new Vector3[4]; ((RectTransform)bouton.transform).GetWorldCorners(coins);
            Vector2 centre = RectTransformUtility.WorldToScreenPoint(null, (coins[0] + coins[2]) / 2); string phrase = bouton.GetComponent<Infobulle>().Phrase;
            UnityEngine.EventSystems.ExecuteEvents.Execute(bouton.gameObject, new UnityEngine.EventSystems.PointerEventData(null) { position = centre }, UnityEngine.EventSystems.ExecuteEvents.pointerEnterHandler);
            bulle.Pas(centre, null, 1); RectTransform feuillet = toile.GetComponentsInChildren<RectTransform>().Single(t => t.name == "Infobulle");
            Assert.That(feuillet.gameObject.activeInHierarchy && feuillet.GetComponentInChildren<Text>().text == phrase && bulle.TexteAffiche == null, Is.True, feuillet.GetComponentInChildren<Text>().text);
            UnityEngine.EventSystems.ExecuteEvents.Execute(bouton.gameObject, new UnityEngine.EventSystems.PointerEventData(null) { position = centre }, UnityEngine.EventSystems.ExecuteEvents.pointerExitHandler);
            Assert.That(toile.GetComponentsInChildren<RectTransform>().Any(t => t.name == "Infobulle"), Is.False);
            bulle.Pas(O, terre, 1); Assert.That(bulle.TexteAffiche, Does.StartWith("Bourg témoin · ")); bulle.Pas(O, null, 1);
            Assert.That(toile.GetComponentsInChildren<RectTransform>().Any(t => t.name == "Infobulle"), Is.False); Assert.That(racine.GetComponentsInChildren<Canvas>().Length, Is.EqualTo(1));
        }
        [Test] public void LaVieilleBoiteDeSurvolSEteintSousLeCabinet()
        {
            var camera = new GameObject("caméra neuve").AddComponent<Camera>();
            try
            {
                racine.GetComponent<CarteDessinee>().camera = camera; var fiche = racine.GetComponent<FicheDeCellule>(); fiche.Demarrer();
                var toile = racine.transform.Find("Toile de la fiche"); Assert.That(toile != null && toile.gameObject.activeInHierarchy, Is.True, "la fiche démarrée après le cabinet doit d'abord être active");
                cabinet.Afficher(); Assert.That(toile.gameObject.activeInHierarchy, Is.False); var actives = racine.GetComponentsInChildren<Canvas>();
                Assert.That(actives.Length == 1 && actives[0].name == "Cabinet", Is.True, string.Join(", ", actives.Select(c => c.name))); fiche.Arreter();
            }
            finally { Object.DestroyImmediate(camera.gameObject); }
        }
        // Lot #963 : la bande des modes et sa légende, en bas à droite de la vue de la carte, ne passent sous aucun panneau.
        static Rect Zone(RectTransform t, float k) // en unités d'écran, origine en haut à gauche, pour une toile de 1920 × k de large
        {
            Assert.That(t.anchorMin, Is.EqualTo(t.anchorMax), t.name + " : ancres étirées"); float x = t.anchorMin.x * 1920 + t.anchoredPosition.x - t.pivot.x * t.sizeDelta.x;
            return new Rect(x * k, ((1 - t.anchorMin.y) * 1080 - t.anchoredPosition.y - (1 - t.pivot.y) * t.sizeDelta.y) * k, t.sizeDelta.x * k, t.sizeDelta.y * k);
        }
        static string Recouvert(Transform toile, Rect zone, float k) => toile.Cast<Transform>().Where(e => e.GetComponent<Image>() is Image i && i.raycastTarget
            && !new[] { "Fond des dossiers", "Infobulle", CalquesCarte.BANDE, CalquesCarte.LEGENDE }.Contains(e.name)).FirstOrDefault(e => zone.Overlaps(Zone((RectTransform)e, k)))?.name;
        [Test] public void La_bande_des_modes_et_sa_legende_restent_a_leur_place()
        {
            Transform toile = racine.transform.Find("Cabinet"); var bande = (RectTransform)toile.Find(CalquesCarte.BANDE); var fond = (RectTransform)toile.Find(CalquesCarte.LEGENDE);
            foreach (var (nom, repere) in new[] { ("Puissances", "banniere"), ("Habitants", "foule"), ("Flux", "fleche") })
            {
                var bouton = bande.Find(nom)?.GetComponent<Button>(); Assert.That(bouton, Is.Not.Null, nom); string phrase = bouton.GetComponent<Infobulle>()?.Phrase;
                Assert.That(!string.IsNullOrWhiteSpace(phrase) && phrase != nom && bouton.transform.Find("Repère " + repere) != null, Is.True, nom + " : phrase « " + phrase + " » ou repère absent");
            }
            Assert.That(toile.Find("Parcourir le monde"), Is.Null, "le panneau « Parcourir le monde » est encore posé");
            Button[] modes = toile.GetComponentsInChildren<Button>(true).Where(b => new[] { "Puissances", "Habitants", "Flux" }.Contains(b.name)).ToArray();
            Assert.That(modes.Length == 3 && modes.Select(b => b.name).Distinct().Count() == 3 && modes.All(b => b.transform.parent == bande), Is.True, string.Join(", ", modes.Select(b => b.transform.parent.name + "/" + b.name)));
            var calques = racine.GetComponent<CalquesCarte>(); var repartition = new RepartitionHabitants(new MondeLu(364, new DateDuMonde(1400, 365), 2, new[] { new CelluleDuMonde(10, 1, -1, -1), new CelluleDuMonde(20, 275000, -1, -1) }));
            foreach (var (texte, mode) in new[] { (CalquesCarte.LegendeDuCalque(null), ModeDeCarte.Puissances), (CalquesCarte.LegendeDuCalque(repartition), ModeDeCarte.Habitants), (CalquesCarte.FLUX, ModeDeCarte.Flux) })
            {
                string detail = CalquesCarte.DetailDuMode(mode); calques.Legender(texte, detail);
                foreach (float echelle in new[] { 1f, 2f / 3f }) Assert.That(CalquesCarte.Lignes(calques.Legende, texte, echelle), Is.InRange(1, CalquesCarte.LIGNES_MAX), mode + " à l'échelle " + echelle);
                Assert.That(calques.Legende.text == texte && fond.GetComponent<Infobulle>().Phrase == texte + "\n" + detail && calques.Legende.transform.parent == fond, Is.True, mode.ToString());
                Assert.That(Zone(fond, 1).yMax, Is.EqualTo(1004f).Within(.01f), mode + " : le bas de la légende");
                foreach (var (largeur, hauteur) in new[] { (1920f, 1080f), (1280f, 720f) }) foreach (var zone in new[] { bande, fond })
                {
                    Rect r = Zone(zone, largeur / 1920); string sous = Recouvert(toile, r, largeur / 1920); Assert.That(sous, Is.Null, zone.name + " recouvre « " + sous + " » en " + largeur + " × " + hauteur + " (" + mode + ")");
                    Assert.That(r.xMin >= 0 && r.yMin >= 0 && r.xMax <= .67f * largeur && r.yMax <= hauteur, Is.True, zone.name + " " + r + " hors de sa place en " + largeur + " × " + hauteur);
                }
            }
            Assert.That(fond.GetComponent<Image>().raycastTarget && bande.parent == toile && fond.parent == toile, Is.True);
            Assert.That(new Rect(24, 872, 1238, 184).Overlaps(Zone(bande, 1)), Is.True, "contre-épreuve : un guide de 1238 de large recouvre la bande");
            Assert.That(Recouvert(toile, new Rect(16, 104, 1100, 160), 1), Is.Not.Null, "contre-épreuve : l'ancienne légende des lieux recouvre un feuillet");
            var etat = racine.GetComponentsInChildren<Text>(true).Single(t => t.name == CabinetDeCarte.ETAT); Assert.That(etat.text, Is.EqualTo("La carte se prépare…")); Assert.That(etat.preferredWidth, Is.LessThanOrEqualTo(600f));
            foreach (var (largeur, hauteur) in new[] { (1920f, 1080f), (1280f, 720f) }) { float k = largeur / 1920; Rect r = Zone(etat.rectTransform, k);
                Assert.That(r.xMin >= 0 && r.yMin >= 0 && r.xMax <= .67f * largeur && r.yMax <= hauteur && !r.Overlaps(Zone(bande, k)) && !r.Overlaps(Zone(fond, k)), Is.True, "l'état " + r + " hors de la vue de la carte, ou sur la bande, en " + largeur + " × " + hauteur); }
        }
        [Test] public void Changer_de_mode_ne_touche_ni_l_horloge_ni_les_lectures()
        {
            int appels = 0; partie = new LecturePartie(() => { appels++; return Lecture<MondeAvecMaisonLu>.Absent("lecture témoin"); }, _ => { appels++; return null; }, () => { appels++; return null; }, _ => { appels++; return null; }); cabinet.Partie = partie;
            var monde = Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(1, new DateDuMonde(1400, 1), 0, new CelluleDuMonde[0]), null)); Poser(partie, "Monde", monde);
            var horlogeDeCarte = racine.GetComponent<HorlogeDeCarte>(); var lue = new HorlogeLue(7, new DateDuMonde(1400, 8), 2); Poser(horlogeDeCarte, "Lue", lue);
            var calques = racine.GetComponent<CalquesCarte>(); Transform bande = racine.transform.Find("Cabinet/" + CalquesCarte.BANDE);
            foreach (var mode in new[] { ModeDeCarte.Flux, ModeDeCarte.Habitants, ModeDeCarte.Puissances }) { bande.Find(mode.ToString()).GetComponent<Button>().onClick.Invoke(); Assert.That(calques.Mode, Is.EqualTo(mode)); }
            Assert.That(appels == 0 && !partie.Occupee && ReferenceEquals(partie.Monde, monde) && !horlogeDeCarte.RequeteEnVol && ReferenceEquals(horlogeDeCarte.Lue, lue), Is.True, appels + " lecture(s), occupée " + partie.Occupee);
            _ = partie.Actualiser(); Assert.That(partie.Occupee, Is.True, "contre-épreuve : une lecture lancée occupe la partie");
        }
        // Lot #1001 : la barre du haut dit la maison, sa part et son grenier, lus aux comptes servis au tick du monde lu.
        const string BARRE = "Lecture de la maison…", ATTENTE = "Comptes en attente du monde", SC1 = "Maison témoin · Prélèvement : 25 % · Grenier : bois : 0 kg · nourriture : 1,23 t";
        static Lecture<ComptesDeMaison> ComptesBarre(string id, long? tick, double? part = 0.25, Dictionary<string, double> grenier = null) => Lecture<ComptesDeMaison>.De(new ComptesDeMaison(
            new MaisonLue(id, "Maison témoin", new SiegeDeMaison(10, 0, "Siège", new PointCarte(1, 2)), new[] { new LieuTenu(10, 0) }, new Dictionary<string, string>()),
            null, part, grenier ?? new Dictionary<string, double> { ["nourriture"] = 1234.5, ["bois"] = 0 }, new FluxDeMaison(0, 0, 0, 0, 0, 0, 0, null), tick));
        string LaBarre(Lecture<ComptesDeMaison> comptes) { Poser(partie, "Comptes", comptes); cabinet.Afficher(); string t = Propre(BARRE); Assert.That(TexteDuMonde.Interdit(t, JOUEUR, B), Is.Null, t); return t; }
        [Test] public void La_barre_egale_les_comptes_servis_au_meme_tick()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); Assert.That(LaBarre(ComptesBarre(JOUEUR, 1)), Is.EqualTo(SC1));
            Text barre = Nomme(BARRE); RectTransform cadre = barre.rectTransform; Assert.That(barre.transform.parent.name, Is.EqualTo("FORGE · Le cabinet"));
            Assert.That(barre.preferredWidth, Is.LessThanOrEqualTo(1872f)); Assert.That(barre.preferredHeight, Is.LessThanOrEqualTo(26f)); Assert.That(cadre.sizeDelta, Is.EqualTo(new Vector2(1872, 26)));
            float bas = -cadre.anchoredPosition.y + cadre.sizeDelta.y; Assert.That(bas, Is.EqualTo(98f)); Assert.That(bas, Is.LessThanOrEqualTo(((RectTransform)barre.transform.parent).sizeDelta.y));
            Assert.That(LaBarre(ComptesBarre(JOUEUR, 1, null, new Dictionary<string, double>())), Is.EqualTo("Maison témoin · Prélèvement : absent · Grenier : vide"));
        }
        [Test] public void Une_barre_lue_un_tick_plus_tot_echoue()
        {
            Publier(JOUEUR, new LieuTenu(10, 0));
            foreach (var (comptes, etape) in new[] { (ComptesBarre(JOUEUR, 0), "tick 0"), (ComptesBarre(JOUEUR, null), "tick non servi"), (ComptesBarre(B, 1), "autre maison"), ((Lecture<ComptesDeMaison>)null, "sans comptes") })
            { string t = LaBarre(comptes); Assert.That(t, Is.EqualTo(ATTENTE), etape); Assert.That(t, Does.Not.Contain("25 %").And.Not.Contain("1,23 t"), etape); }
            Assert.That(LaBarre(ComptesBarre(JOUEUR, 1)), Is.EqualTo(SC1), "remis au tick du monde");
            Assert.That(LaBarre(Lecture<ComptesDeMaison>.Absent("refus témoin")), Is.EqualTo("Comptes indisponibles : refus témoin"));
        }
        [Test] public void Sans_maison_la_barre_le_dit()
        {
            Proposer(); Assert.That(Propre(BARRE), Is.EqualTo("Aucune maison choisie"));
            Poser(partie, "Comptes", ComptesBarre(JOUEUR, 1)); cabinet.Afficher(); Assert.That(Propre(BARRE), Is.EqualTo("Aucune maison choisie"), "des comptes sans maison du joueur ne s'affichent pas");
            Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.Absent("service coupé")); cabinet.Afficher(); Assert.That(Propre(BARRE), Is.EqualTo("Maison indisponible : service coupé"));
            Poser(partie, "Monde", null); cabinet.Afficher(); Assert.That(Propre(BARRE), Is.EqualTo(BARRE));
            Assert.That(racine.GetComponentsInChildren<Button>().Count(b => b.transform.parent.name == "FORGE · Le cabinet"), Is.EqualTo(3), "la barre n'est pas une commande");
        }
        // Lot #1002 : « Terres et comptes » et « Autres maisons » sont deux icônes de la barre du haut, chacune avec son motif et sa phrase ; leurs feuillets ne recouvrent jamais la barre.
        static Rect Monde(RectTransform t) { var c = new Vector3[4]; t.GetWorldCorners(c); return Rect.MinMaxRect(c.Min(v => v.x), c.Min(v => v.y), c.Max(v => v.x), c.Max(v => v.y)); }
        [Test] public void Chaque_icone_de_la_barre_a_sa_phrase_et_son_motif()
        {
            Transform toile = racine.transform.Find("Cabinet"), conteneur = toile.Find("FORGE · Le cabinet/" + CabinetDeCarte.DOSSIERS); Assert.That(conteneur, Is.Not.Null, "dossiers de la barre introuvables");
            Button[] icones = conteneur.GetComponentsInChildren<Button>(true).OrderBy(b => ((RectTransform)b.transform).anchoredPosition.x).ToArray();
            Assert.That(icones.Select(b => b.name), Is.EqualTo(new[] { "Terres et comptes", "Autres maisons" }));
            string[] titres = { "Terres et comptes", "Les autres maisons" }, motifs = { "coffre", "maisons" };
            for (int i = 0; i < 2; i++)
            {
                Button icone = icones[i]; string phrase = icone.GetComponent<Infobulle>()?.Phrase, autre = icones[1 - i].GetComponent<Infobulle>()?.Phrase;
                Assert.That(((RectTransform)icone.transform).sizeDelta, Is.EqualTo(new Vector2(56, 44)), icone.name);
                Assert.That(icone.GetComponentsInChildren<Text>().Select(t => t.text), Is.Empty, icone.name + " écrit encore son nom");
                Assert.That(icone.transform.Find("Repère " + motifs[i]) != null && icone.transform.Find("Repère livre") == null, Is.True, icone.name + " : motif absent, ou livre du Menu");
                Assert.That(!string.IsNullOrWhiteSpace(phrase) && phrase != icone.name && phrase != autre && phrase.StartsWith(titres[i] + " : ", StringComparison.Ordinal), Is.True, icone.name + " : « " + phrase + " »");
                var feuillet = toile.Cast<Transform>().Single(t => t.name == titres[i] && t.GetComponentInChildren<ScrollRect>(true) != null).gameObject;
                Assert.That(feuillet.activeSelf, Is.False, titres[i] + " ouvert d'avance"); icone.onClick.Invoke(); Assert.That(feuillet.activeSelf, Is.True, titres[i] + " reste fermé au clic");
                icone.onClick.Invoke(); Assert.That(feuillet.activeSelf, Is.False, titres[i] + " reste ouvert au second clic");
            }
            foreach (var nom in new[] { "Terres et comptes", "Autres maisons" }) { Assert.That(toile.GetComponentsInChildren<Button>(true).Count(b => b.name == nom), Is.EqualTo(1), nom + " : un seul bouton dans la toile");
                Assert.That(toile.Find("Parcourir le monde"), Is.Null, "le panneau « Parcourir le monde » est encore posé");
                Assert.That(toile.GetComponentsInChildren<Button>(true).Where(b => b.name == nom).All(b => b.transform.parent == conteneur), Is.True, nom + " hors des dossiers de la barre"); }
            Assert.Throws<ArgumentException>(() => EmblemeCommande.Icone(conteneur, "Sans motif", 0, null, "témoin"));
        }
        [Test] public void Aucun_dossier_ne_recouvre_la_barre()
        {
            Proposer(); Transform toile = racine.transform.Find("Cabinet"); var bandeau = (RectTransform)toile.Find("FORGE · Le cabinet"); var conteneur = (RectTransform)bandeau.Find(CabinetDeCarte.DOSSIERS);
            foreach (var icone in conteneur.GetComponentsInChildren<Button>()) icone.onClick.Invoke();
            Button Commande(string nom) => toile.GetComponentsInChildren<Button>(true).Single(b => b.name == nom); Commande("Menu").onClick.Invoke(); Canvas.ForceUpdateCanvases();
            Assert.That(racine.GetComponent<MenuCabinet>().Ouvert && new[] { "Terres et comptes", "Les autres maisons" }.All(n => toile.Cast<Transform>().Any(t => t.name == n && t.gameObject.activeSelf && t.GetComponentInChildren<ScrollRect>(true) != null)), Is.True, "les deux feuillets et le menu doivent être ouverts");
            Rect barre = Monde(bandeau), reduite = Rect.MinMaxRect(barre.xMin + .5f, barre.yMin + .5f, barre.xMax - .5f, barre.yMax - .5f);
            var panneaux = toile.Cast<Transform>().Where(t => t != bandeau && t.Find("Filet") != null).Cast<RectTransform>().ToArray();
            Assert.That(panneaux.Select(p => p.name), Is.SupersetOf(new[] { "Terres et comptes", "Les autres maisons", "Menu du cabinet", "Plan du bourg", "Votre maison", "Territoire conservé" }));
            Assert.That(panneaux.Select(p => p.name), Has.None.EqualTo("Parcourir le monde"), "le panneau « Parcourir le monde » est encore posé");
            foreach (var p in panneaux) Assert.That(Monde(p).Overlaps(reduite), Is.False, "« " + p.name + " » recouvre la barre : " + Monde(p) + " sur " + barre);
            Rect icones = Monde(conteneur); var c = new Vector3[4]; conteneur.GetWorldCorners(c); var cadre = (RectTransform)toile;
            float bas = c.Max(v => cadre.rect.yMax - cadre.InverseTransformPoint(v).y);
            Assert.That(barre.Contains(icones.min) && barre.Contains(icones.max) && bas <= 70, Is.True, "les icônes " + icones + " (bas " + bas + ") sortent du bandeau " + barre + " ou passent sous le filet");
            foreach (var voisin in new[] { Nomme("Lecture de la date…").rectTransform, Nomme(BARRE).rectTransform }.Concat(new[] { "Menu", "Ralentir", "Pause / Reprendre", "Accélérer" }.Select(n => (RectTransform)Commande(n).transform)))
                Assert.That(icones.Overlaps(Monde(voisin)), Is.False, "les icônes " + icones + " recouvrent « " + voisin.name + " » " + Monde(voisin));
            Text date = Nomme("Lecture de la date…"); Assert.That(date.rectTransform.sizeDelta.x, Is.EqualTo(600f));
            foreach (string texte in new[] { "Date indisponible : le monde ne répond pas", HorlogeDeCarte.Decrire(new HorlogeLue(364, new DateDuMonde(1400, 365), 1.5)) }) { date.text = texte; Assert.That(date.preferredWidth, Is.LessThanOrEqualTo(600f), texte); }
        }
        // Lot #1003 : le panneau « Parcourir le monde » quitte le bas de la carte ; ses commandes restent à leur place, son aide passe au Menu, l'état de la carte au centre de sa vue.
        [Test] public void Aucun_panneau_Parcourir_le_monde_ne_reste()
        {
            const string NOM = "Parcourir le monde"; Transform toile = racine.transform.Find("Cabinet");
            Transform[] Restes() => racine.GetComponentsInChildren<Transform>(true).Where(t => t.name == NOM || t.TryGetComponent<Text>(out var texte) && texte.text.Contains(NOM)).ToArray();
            Assert.That(Restes().Select(t => t.name), Is.Empty);
            Assert.That(System.IO.File.ReadAllText("Assets/Interface/CabinetDeCarte.cs"), Does.Not.Contain(NOM));
            Button[] boutons = toile.GetComponentsInChildren<Button>(true);
            Button Seul(string nom) { Button[] trouves = boutons.Where(b => b.name == nom).ToArray(); Assert.That(trouves, Has.Length.EqualTo(1), nom + " : un seul bouton dans la toile"); return trouves[0]; }
            Transform bande = toile.Find(CalquesCarte.BANDE), conteneur = toile.Find("FORGE · Le cabinet/" + CabinetDeCarte.DOSSIERS);
            foreach (var nom in new[] { "Puissances", "Habitants", "Flux" }) Assert.That(Seul(nom).transform.parent, Is.SameAs(bande), nom + " hors de la bande des modes");
            foreach (var nom in new[] { "Terres et comptes", "Autres maisons" }) Assert.That(Seul(nom).transform.parent, Is.SameAs(conteneur), nom + " hors des dossiers de la barre");
            Button menu = Seul("Menu"); Assert.That(menu.transform.parent, Is.SameAs(toile), "le Menu n'est pas un enfant direct de la toile"); Assert.That(menu.GetComponent<Infobulle>().Phrase, Does.EndWith(CabinetDeCarte.AIDE));
            Assert.That(toile.Find(CabinetDeCarte.ETAT)?.GetComponent<Text>(), Is.Not.Null, "l'état de la carte n'est pas un enfant direct de la toile");
            var temoin = SocleInterface.Panneau(toile, NOM, 24, 872, 740, 184); // contre-épreuve : le panneau remis
            try { Assert.That(Restes(), Does.Contain((Transform)temoin), "contre-épreuve : Restes() ne voit pas le panneau remis"); }
            finally { Object.DestroyImmediate(temoin.gameObject); }
            Assert.That(Restes(), Is.Empty);
        }
        [Test] public void L_etat_de_la_carte_parle_au_centre_de_sa_vue()
        {
            var dessinee = racine.GetComponent<CarteDessinee>(); Text etat = racine.transform.Find("Cabinet/" + CabinetDeCarte.ETAT).GetComponent<Text>();
            Poser(dessinee, "CellulesServies", -1); cabinet.Afficher();
            Assert.That(etat.gameObject.activeSelf && etat.text == "La carte se prépare…", Is.True, "carte non servie : « " + etat.text + " »");
            Rect r = Zone(etat.rectTransform, 1); Assert.That(Vector2.Distance(r.center, new Vector2(.67f * 1920 / 2, 540)), Is.LessThanOrEqualTo(1f), "l'état " + r + " hors du centre de la vue"); Assert.That(etat.raycastTarget, Is.False); Assert.That(etat.alignment, Is.EqualTo(TextAnchor.MiddleCenter));
            Poser(dessinee, "CellulesServies", 12); cabinet.Afficher(); Assert.That(etat.gameObject.activeSelf, Is.False, "carte servie : l'état reste affiché");
            Poser(dessinee, "CellulesServies", -1); cabinet.Afficher(); Assert.That(etat.gameObject.activeSelf, Is.True, "remise à −1 : l'état ne revient pas");
        }
    }
}
