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
        [TearDown] public void Fermer() { if (ecran != null) { camera.targetTexture = null; Object.DestroyImmediate(ecran); ecran = null; } racine.GetComponent<CarteDessinee>().Arreter(); Object.DestroyImmediate(racine); }

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

        // Une fois la maison servie, l'accueil se ferme ; « Votre maison », ouvert de son icône, et la fiche d'une terre gardée arrêtent les clics.
        [Test] public void Les_dossiers_ouverts_arretent_les_clics()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); IconeDeLaMaison().onClick.Invoke(); cabinet.Garder(Terre(7, "Ville test")); cabinet.Afficher();
            foreach (var nom in new[] { "Votre maison", "Territoire conservé" })
            {
                var panneau = racine.transform.Find("Cabinet/" + nom).GetComponent<Image>(); // le panneau, enfant de la toile ; l'icône « Votre maison » est dans la barre
                Assert.That(panneau.gameObject.activeInHierarchy, Is.True, nom + " fermé après son clic");
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
            Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); Poser(partie, "Monde", null); // le territoire se lit une fois l'accueil fermé, qui ne revient pas
            cabinet.Garder(new CelluleDeCarte(7, new PolygoneDeCarte[0], new IdentiteDeCarte(1, "Puissance test"),
                null, new[] { new VilleDeCarte("Ville test", 12, new PointCarte(0, 0)) }));
            racine.GetComponent<FicheDeCellule>().Quitter();
            cabinet.Afficher(); racine.GetComponent<DossierTerritoire>().Pas(0);
            Assert.That(cabinet.Retenue?.CellId == 7 && racine.transform.Find("Cabinet/" + CabinetDeCarte.TERRITOIRE).gameObject.activeSelf, Is.True, "la terre gardée tombe avec le survol");
            Assert.That(Territoire(), Does.StartWith(DossierTerritoire.PAYS_EN_LECTURE + "\n"), "la fiche de la terre gardée ne s'écrit plus");
        }

        const string JOUEUR = "maison-joueur", B = "maison-b", C = "maison-c";
        LieuxDeCarte lieux; CarteDessinee carte; LecturePartie partie; Camera camera; double horloge;
        [Test] public void LeCabinetConstruitUneSeuleVueDesLieux() { int avant = racine.GetComponents<MonoBehaviour>().Length; Assert.That(racine.GetComponents<LieuxDeCarte>(), Has.Length.EqualTo(1)); cabinet.Construire(); Assert.That(racine.GetComponents<LieuxDeCarte>(), Has.Length.EqualTo(1)); Assert.That(racine.GetComponents<MonoBehaviour>().Length, Is.EqualTo(avant)); }
        [Test] public void LesLieuxDesCellulesTenuesSontLusSansRienPoser()
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); var vus = new List<long>();
            Servir(cell => { vus.Add(cell); return Reponse(cell, 4, false, 3); }); Assert.That(vus, Is.EquivalentTo(new[] { 10L, 20L }), lieux.TexteLegende); Assert.That(lieux.TexteLegende, Does.Contain("\nAlba · relevé au jour 5 de 1400").And.Contain("\nDara · relevé au jour 5 de 1400").And.Contain(LieuxDeCarte.ENTETE));
            // Les lieux du joueur (10-0 et 20-1) voient partir plus de gens qu'il n'en arrive : eux seuls sont en alerte, pas ceux de B ni de C ; et rien n'est posé sur la carte.
            Assert.That(Alertes(), Is.EqualTo("10-0,20-1")); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(1)); Assert.That(Posees(), Is.Empty, "la lecture des lieux a posé quelque chose sur la carte");
            // Servie renversée, la même réponse donne le même ensemble trié et la même version.
            Servir(cell => Reponse(cell, 11, true, 3)); Assert.That(lieux.TexteLegende, Does.Contain("relevé au jour 12 de 1400")); Assert.That(Alertes(), Is.EqualTo("10-0,20-1")); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(1), "une relecture identique change la version"); Assert.That(Posees(), Is.Empty);
            Servir(cell => Reponse(cell, 12, false, 1)); Assert.That(lieux.TexteLegende, Does.Contain("relevé au jour 13 de 1400")); Assert.That(Alertes(), Is.Empty); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(2)); Assert.That(Posees(), Is.Empty);
        }
        [TestCase(JOUEUR, 7L, 2L, true)] [TestCase(JOUEUR, 9L, 2L, true)] [TestCase(JOUEUR, 2L, 7L, false)] [TestCase(JOUEUR, 7L, 7L, false)] [TestCase(JOUEUR, 0L, 0L, false)] [TestCase(B, 7L, 2L, false)] [TestCase(B, 9L, 2L, false)] [TestCase(B, 2L, 7L, false)] [TestCase(B, 7L, 7L, false)] [TestCase(B, 0L, 0L, false)] public void LAlerteSuitLeSoldeDesLieuxDuJoueur(string maitre, long partis, long arrives, bool alerte)
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0)); Servir(_ => LectureLieu.De(Cellule(10, 3, Place(10, 0, 1000, 2000, maitre, partis, arrives))));
            Assert.That(Alertes(), Is.EqualTo(alerte ? "10-0" : ""), maitre + " " + partis + "/" + arrives); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(alerte ? 1 : 0)); Assert.That(Posees(), Is.Empty);
            if (partis == 0 && arrives == 0) Assert.That(lieux.TexteLegende.Contains("absent"), Is.False, lieux.TexteLegende);
        }
        [Test] public void LAlertePeutDisparaitreEtReparaitre()
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0)); long tick = 4; FluxDeLieu flux = new FluxDeLieu(0, 7, 2); string cause = null;
            void Lire() => Servir(_ => LectureLieu.De(Cellule(10, tick, new LieuPlace(0, new PointCarte(1000, 2000), JOUEUR, flux, cause, nom: NomDe(10, 0)))));
            void Passer() { lieux.Pas(horloge); var fin = DateTime.UtcNow.AddSeconds(5); while (lieux.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); lieux.Pas(horloge); horloge += LieuxDeCarte.PERIODE_S; }
            Lire(); Assert.That(Alertes(), Is.EqualTo("10-0")); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(1));
            tick = 5; Lire(); Assert.That(lieux.TexteLegende, Does.Contain("relevé au jour 6 de 1400")); Assert.That(Alertes(), Is.EqualTo("10-0")); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(1), "une relecture identique change la version");
            flux = new FluxDeLieu(0, 7, 7); tick = 6; Lire(); Assert.That(Alertes(), Is.Empty); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(2));
            flux = null; cause = "flux non fournis"; tick = 7; Lire(); Assert.That(lieux.TexteLegende, Does.Contain("\nAlba : flux non fournis").And.Contain("relevé au jour 8 de 1400")); Assert.That(Alertes(), Is.Empty, "un lieu sans flux servi est en alerte"); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(2));
            flux = new FluxDeLieu(0, 7, 2); cause = null; tick = 8; Lire(); Assert.That(lieux.TexteLegende, Does.Not.Contain("flux non fournis").And.Contain("relevé au jour 9 de 1400")); Assert.That(Alertes(), Is.EqualTo("10-0")); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(3));
            // La maison change : l'alerte de l'ancienne ne reste pas.
            Publier(C, new LieuTenu(10, 0)); Passer(); Assert.That(Alertes(), Is.Empty); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(4)); Assert.That(lieux.Peint, Is.True);
            Publier(JOUEUR, new LieuTenu(10, 0)); Passer(); tick = 9; Lire(); Assert.That(Alertes(), Is.EqualTo("10-0")); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(5));
            // La maison se vide : plus d'alerte, plus de lieux peints.
            Poser(partie, "Monde", null); Passer(); Assert.That(Alertes(), Is.Empty); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(6)); Assert.That(lieux.Peint, Is.False);
        }
        [Test] public void LesAbsencesEtLaNavigationRestentHonnetes()
        {
            Preparer(); int n = 0; lieux.Lecteur = _ => { n++; return null; }; lieux.Pas(0); lieux.Pas(3); Assert.That(n == 0 && Alertes() == "" && Posees().Length == 0, Is.True);
            var porte = new System.Threading.Tasks.TaskCompletionSource<bool>(); lieux.Lecteur = cell => { System.Threading.Interlocked.Increment(ref n); porte.Task.Wait(8000); return Complet(cell, 3); };
            Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(20, 0)); lieux.Pas(0); var fin = DateTime.UtcNow.AddSeconds(5); while (n < 1 && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); lieux.Pas(1); Assert.That(n, Is.EqualTo(1), lieux.TexteLegende);
            Publier("maison-ancienne", new LieuTenu(10, 0), new LieuTenu(20, 0)); porte.TrySetResult(true); fin = DateTime.UtcNow.AddSeconds(5); while (lieux.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); lieux.Pas(1);
            Assert.That(Alertes() == "" && n == 2 && !lieux.LectureEnVol, Is.True, lieux.TexteLegende); horloge = 2; Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); Servir(cell => Complet(cell, 8)); Assert.That(Alertes(), Is.EqualTo("10-0,20-0"));
            void Reprise(Func<long, LectureLieu> mauvais, string alertes, string texte) { Servir(mauvais); Assert.That(Alertes(), Is.EqualTo(alertes), lieux.TexteLegende); Assert.That(lieux.TexteLegende, Does.Contain(texte)); Servir(cell => Complet(cell, 8)); Assert.That(Alertes(), Is.EqualTo("10-0,20-0")); }
            Reprise(cell => cell == 10 ? LectureLieu.Absent("lecture refusée") : Complet(cell, 8), "20-0", "\nTerre sans lieux lus : lecture refusée");
            Reprise(cell => cell == 10 ? LectureLieu.De(Cellule(10, 8)) : Complet(cell, 8), "20-0", "\nTerre sans lieux lus : liste vide");
            Reprise(cell => cell == 10 ? LectureLieu.De(new Lieu(10, 8, 1400, 1, 1, new Dictionary<string, double>(), 0, 0, lieux: null, absenceDesLieux: "clé absente : lieux")) : Complet(cell, 8), "20-0", "\nTerre sans lieux lus : clé absente : lieux");
            // Un lieu du joueur sans point reste en alerte : son flux est servi ; son point absent se dit dans le relevé.
            Reprise(cell => cell == 10 ? LectureLieu.De(Cellule(10, 8, Place(10, 0, 1000, 2000, JOUEUR, 2, 1), new LieuPlace(1, null, JOUEUR, new FluxDeLieu(0, 2, 1), nom: NomDe(10, 1)))) : Complet(cell, 8), "10-0,10-1,20-0", "\nAlba · Brivas : point absent");
            Reprise(cell => cell == 10 ? LectureLieu.De(Cellule(10, 8, Place(10, 0, 1000, 2000, JOUEUR, 2, 1), new LieuPlace(1, new PointCarte(4000, 2000), null, new FluxDeLieu(0, 2, 1), nom: NomDe(10, 1)))) : Complet(cell, 8), "10-0,20-0", "\nAlba · Brivas : maître absent");
            Vector2 centre = carte.Vue.Centre; float echelle = carte.Vue.Echelle; Vector3 pos = camera.transform.position; Color teinte = carte.TeinteDe(10).Value; string alertes = Alertes(); int version = lieux.VersionDesAlertes; Servir(cell => Complet(cell, 9)); Servir(cell => Complet(cell, 10)); Servir(cell => Complet(cell, 11));
            Assert.That(Alertes() == alertes && lieux.VersionDesAlertes == version && carte.Vue.Centre == centre && carte.Vue.Echelle == echelle && camera.transform.position == pos && carte.TeinteDe(10) == teinte, Is.True); Assert.That(Posees(), Is.Empty);
        }
        // Flèches du prélèvement et du dû.
        FlechesDeCarte fleches;
        [Test] public void LeCabinetConstruitUneSeuleVueDesFleches() { Assert.That(racine.GetComponents<FlechesDeCarte>(), Has.Length.EqualTo(1)); cabinet.Construire(); Assert.That(racine.GetComponents<FlechesDeCarte>(), Has.Length.EqualTo(1)); }
        [TestCase(0d, 0f)] [TestCase(1000d, 4f)] [TestCase(200000d, 4f)] [TestCase(218086d, 4.36172f)] [TestCase(300000d, 6f)] [TestCase(400000d, 8f)] [TestCase(10000000d, 8f)] public void LEpaisseurEstAbsolueEtPlafonnee(double kg, float km) => Assert.That(FlechesDeCarte.Epaisseur(kg), Is.EqualTo(km).Within(1e-4f));
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
        // Les deux légendes nomment chaque terre par son bourg, chaque lieu par son nom servi, et pèsent en tonnes.
        const string ABSENT = "TexteDuMonde : absence déclarée par le monde : ";
        [Test] public void La_legende_des_lieux_nomme_date_et_declare_l_absent()
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(10, 2), new LieuTenu(20, 0), new LieuTenu(30, 0));
            LogAssert.Expect(LogType.Log, ABSENT + "nom absent pour 10-0"); LogAssert.Expect(LogType.Log, ABSENT + "flux absents au tick 4"); LogAssert.Expect(LogType.Log, ABSENT + "lieu 30 : délai dépassé");
            Servir(cell => cell == 30 ? LectureLieu.Absent("lieu 30 : délai dépassé") : LectureLieu.De(cell == 20 ? Cellule(20, 4, Place(20, 0, 8000, 3000, B, 1, 1))
                : Cellule(10, 4, new LieuPlace(0, new PointCarte(1000, 2000), JOUEUR, new FluxDeLieu(0, 1, 1), absenceDuNom: "nom absent pour 10-0"), new LieuPlace(1, new PointCarte(4000, 2000), JOUEUR, null, "flux absents au tick 4", nom: "Brivas"), new LieuPlace(2, null, JOUEUR, new FluxDeLieu(0, 1, 1)))));
            string t = lieux.TexteLegende; const string SANS = "\nBourg sans nom (déclaré absent par le monde)";
            Assert.That(t, Does.Contain(SANS + " · relevé au jour 5 de 1400").And.Contain(SANS + " · Brivas : déclaré absent par le monde").And.Contain(SANS + " · lieu sans nom (nom non fourni) : point absent").And.Contain("\nDara · relevé au jour 5 de 1400").And.Contain("\nTerre sans lieux lus : déclaré absent par le monde"));
            Assert.That(TexteDuMonde.Interdit(t, JOUEUR, B, C) ?? TexteDuMonde.SansUnite(t), Is.Null, t); Assert.That(Posees(), Is.Empty, "le relevé est dit, mais rien n'est posé");
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
        // Plus de légende flottante ; les lieux parlent dans la légende de la carte politique, les flèches dans celle des vivres, leurs relevés dans l'infobulle.
        static readonly string[] FLOTTANTES = { "Légende des lieux", "Fond de la légende", "Légende des flèches", "Fond des flèches" };
        string Flottante() => racine.transform.Find("Cabinet").GetComponentsInChildren<Transform>(true).Select(t => t.name).FirstOrDefault(FLOTTANTES.Contains);
        [Test] public void Les_lieux_parlent_dans_la_legende_de_la_carte_politique()
        {
            Preparer(); fleches = racine.GetComponent<FlechesDeCarte>(); var calques = racine.GetComponent<CalquesCarte>(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); Servir(cell => Reponse(cell, 4, false)); Assert.That(Flottante(), Is.Null); Assert.That(lieux.Peint, Is.True);
            var politique = new LectureDuMode(ModeDeCarte.Politique, null, null, null, null, lieux.EnAlerte);
            string legende = politique.Legende, detail = CalquesCarte.DetailDuMode(politique, lieux, fleches, null); Assert.That(legende, Is.EqualTo("puissance · " + CalquesCarte.ALERTE + " · " + CalquesCarte.TERRE_OUVERTE));
            Assert.That(detail, Is.EqualTo(CalquesCarte.DetailDuMode(ModeDeCarte.Politique) + lieux.TexteLegende.Substring(LieuxDeCarte.ENTETE.Length)).And.Contain("\nAlba · relevé au jour 5 de 1400").And.Contain("\nDara · relevé au jour 5 de 1400"));
            Assert.DoesNotThrow(() => calques.Legender(politique.Echelle, detail)); string bulle = racine.transform.Find("Cabinet/" + CalquesCarte.LEGENDE).GetComponent<Infobulle>().Phrase;
            Assert.That(bulle, Is.EqualTo(legende + "\n" + detail)); Assert.That(TexteDuMonde.Interdit(bulle, JOUEUR, B, C) ?? TexteDuMonde.SansUnite(bulle), Is.Null, bulle);
            Assert.That(bulle.Split(new[] { LieuxDeCarte.ENTETE }, StringSplitOptions.None).Length, Is.EqualTo(2), "l'en-tête des lieux une seule fois, dans l'infobulle : " + bulle);
            Assert.That(CalquesCarte.DetailDuMode(politique, null, null, null), Is.EqualTo(CalquesCarte.DetailDuMode(ModeDeCarte.Politique)), "contre-épreuve : sans vue des lieux");
            Assert.Throws<ArgumentException>(() => calques.Legender(new EchelleDuMode(false, new[] { Color.white, Color.red, Color.black }, "pays", LieuxDeCarte.ENTETE, "trait"), detail), "contre-épreuve : la phrase des lieux ne tient pas dans une étiquette");
        }
        // Le survol d'un bouton de mode : son infobulle ne recouvre pas le cadre de la légende, qu'elle masquerait sans la zone à éviter.
        static Rect EnPixels(RectTransform t) { var c = new Vector3[4]; t.GetWorldCorners(c); return Rect.MinMaxRect(c[0].x, c[0].y, c[2].x, c[2].y); } // la toile du cabinet est en surimpression : le monde y est l'écran
        [Test] public void L_infobulle_d_un_mode_ne_recouvre_pas_la_legende()
        {
            var calques = racine.GetComponent<CalquesCarte>(); var fond = (RectTransform)racine.transform.Find("Cabinet/" + CalquesCarte.LEGENDE); var feuille = (Func<RectTransform>)(() => (RectTransform)racine.transform.Find("Cabinet/Infobulle")); int jugees = 0;
            foreach (ModeDeCarte mode in Enum.GetValues(typeof(ModeDeCarte)))
            {
                var bouton = calques.BoutonDu(mode); var bulle = bouton.GetComponent<Infobulle>(); var survol = new UnityEngine.EventSystems.PointerEventData(null) { position = EnPixels((RectTransform)bouton.transform).center };
                Assert.That(bulle.eviter, Is.SameAs(fond), mode + " : la légende n'est pas la zone à éviter");
                bulle.OnPointerEnter(survol); Rect avec = EnPixels(feuille()), legende = EnPixels(fond); Assert.That(avec.Overlaps(legende), Is.False, mode + " : l'infobulle " + avec + " recouvre la légende " + legende);
                bulle.eviter = null; bulle.OnPointerEnter(survol); Rect sans = EnPixels(feuille()); Assert.That(sans.Overlaps(legende), Is.True, mode + " : contre-épreuve, sans zone l'infobulle " + sans + " ne recouvre pas la légende " + legende);
                bulle.eviter = fond; jugees++;
            }
            Assert.That(jugees, Is.EqualTo(5), "boutons jugés");
        }
        [Test] public void Les_fleches_ne_se_montrent_qu_en_mode_Vivres()
        {
            Preparer(); fleches = racine.GetComponent<FlechesDeCarte>(); var calques = racine.GetComponent<CalquesCarte>(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); const double a = 100000, b = 218086;
            fleches.Lecteur = _ => Lecture<ComptesDeMaison>.De(new ComptesDeMaison(new MaisonLue(JOUEUR, "Maison", new SiegeDeMaison(10, 0, "Siège", new PointCarte(1, 2)), new LieuTenu[0], new Dictionary<string, string>()), null, 0.6, null, new FluxDeMaison(0, 0, 0, 0, 0, 0, 0, null)));
            Servir(cell => LectureLieu.De(cell == 10 ? Cellule(10, 5, new LieuPlace(0, new PointCarte(1, 2), JOUEUR, new FluxDeLieu(1234.4, 0, 0), nom: NomDe(10, 0)), new LieuPlace(1, new PointCarte(30001, 2), JOUEUR, new FluxDeLieu(a, 0, 0), nom: NomDe(10, 1)), new LieuPlace(2, new PointCarte(-29999, 2), B, new FluxDeLieu(90000, 0, 0), nom: NomDe(10, 2)))
                : Cellule(20, 5, new LieuPlace(0, new PointCarte(1, 40002), JOUEUR, new FluxDeLieu(b, 0, 0), nom: NomDe(20, 0)))));
            var noms = new[] { "Flèche 10-1", "Flèche 20-0" }; var tige = racine.transform.Find(FlechesDeCarte.RACINE); Transform bande = racine.transform.Find("Cabinet/" + CalquesCarte.BANDE); Assert.That(Fleches(), Is.EquivalentTo(noms)); Assert.That(tige.gameObject.activeSelf, Is.False, "le cabinet s'ouvre sur la carte politique : flèches cachées");
            foreach (var (mode, visibles) in new[] { (ModeDeCarte.Vivres, true), (ModeDeCarte.Population, false), (ModeDeCarte.Relief, false), (ModeDeCarte.Guerres, false), (ModeDeCarte.Politique, false), (ModeDeCarte.Vivres, true) }) { bande.Find(mode.ToString()).GetComponent<Button>().onClick.Invoke(); fleches.Pas(horloge); Assert.That(tige.gameObject.activeSelf, Is.EqualTo(visibles), mode.ToString()); Assert.That(Fleches(), Is.EquivalentTo(noms), mode.ToString()); }
            var servis = new LieuxLus(4, new DateDuMonde(1400, 5), 2, new[] { new CelluleServie(10, new[] { new LieuServi(0, 1, 1, 0) }), new CelluleServie(20, new[] { new LieuServi(0, 1, 1, 3) }) });
            var vivres = new LectureDuMode(ModeDeCarte.Vivres, servis, null, null, null);
            Assert.That(Flottante(), Is.Null); string detail = CalquesCarte.DetailDuMode(vivres, lieux, fleches, null); Assert.DoesNotThrow(() => calques.Legender(vivres.Echelle, detail));
            string bulle = racine.transform.Find("Cabinet/" + CalquesCarte.LEGENDE).GetComponent<Infobulle>().Phrase; Assert.That(bulle, Is.EqualTo(vivres.Legende + "\n" + detail)); Assert.That(TexteDuMonde.Interdit(bulle, JOUEUR, B, C) ?? TexteDuMonde.SansUnite(bulle), Is.Null, bulle);
            Assert.That(detail, Is.EqualTo(CalquesCarte.DetailDuMode(ModeDeCarte.Vivres) + vivres.Vivres.Detail + "\n" + fleches.TexteLegende).And.Contain(FlechesDeCarte.ENTETE).And.Contain("\nAlba · Brivas → Siège : " + TexteDuMonde.Masse(100000)));
            Assert.Throws<ArgumentException>(() => calques.Legender(FlechesDeCarte.ENTETE + "\n" + FlechesDeCarte.ENTETE, detail), "contre-épreuve : l'en-tête entier des flèches ne tient pas dans la légende");
        }
        void Du(Func<string, Lecture<ComptesDeMaison>> lire) { fleches.Lecteur = lire; fleches.Pas(horloge); var fin = DateTime.UtcNow.AddSeconds(5); while (fleches.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); Assert.That(fleches.LectureEnVol, Is.False); fleches.Pas(horloge); horloge += FlechesDeCarte.PERIODE_S; }
        string[] Fleches() { var r = racine.transform.Find(FlechesDeCarte.RACINE); return r == null ? new string[0] : r.Cast<Transform>().Select(e => e.name).ToArray(); }
        void Fleche(string nom, PointCarte depart, double kg, PointCarte? arrivee = null)
        {
            var f = racine.transform.Find(FlechesDeCarte.RACINE + "/Flèche " + nom); var v = f.GetComponent<MeshFilter>().sharedMesh.vertices; Vector3 a = carte.PositionSurLaCarte(depart, FlechesDeCarte.HAUTEUR).Value, b = carte.PositionSurLaCarte(arrivee ?? new PointCarte(1, 2), FlechesDeCarte.HAUTEUR).Value, pied = (v[0] + v[1]) / 2f, pointe = v[v.Length - 1];
            // La flèche est un ruban drapé : sa première tranche est son pied, sa dernière sa pointe, et chaque sommet est à sa hauteur au-dessus du sol.
            float APlat(Vector3 p, Vector3 q) => new Vector2(p.x - q.x, p.z - q.z).magnitude;
            Assert.That(APlat(pied, a) < 1e-2f && APlat(pointe, b) < 1e-2f && Vector3.Dot(pointe - pied, b - a) > 0f && f.GetComponent<Collider>() == null, Is.True, nom + " pied " + pied + " pointe " + pointe);
            Assert.That(v.All(p => Mathf.Abs(p.y - carte.SurLeSol(p.x, p.z, FlechesDeCarte.HAUTEUR).y) < 1e-4f), Is.True, nom + " : un sommet de la flèche n'est pas posé sur le sol");
            Assert.That(v.Length % 2 == 0 && v.Length >= 8, Is.True, nom + " : " + v.Length + " sommets, deux par tranche de la hampe et de la pointe");
            // Deux tranches qui se suivent ne sont jamais à plus d'un pas de drapé l'une de l'autre : entre elles, le ruban ne peut pas couper le relief.
            float plusLong = 0f; for (int k = 2; k < v.Length; k += 2) plusLong = Mathf.Max(plusLong, APlat((v[k] + v[k + 1]) / 2f, (v[k - 2] + v[k - 1]) / 2f));
            Assert.That(plusLong, Is.LessThanOrEqualTo(CarteDessinee.PAS_DU_DRAPE_KM + 1e-3f), nom + " : deux tranches du ruban à " + plusLong + " km l'une de l'autre");
            Assert.That(APlat(pied, pointe), Is.GreaterThan(CarteDessinee.PAS_DU_DRAPE_KM), "échantillon vide : la flèche " + nom + " tient dans un seul pas");
            Assert.That(APlat(v[0], v[1]), Is.EqualTo(FlechesDeCarte.Epaisseur(kg)).Within(1e-2f), nom + " : la hampe n'a pas l'épaisseur de ce qui est envoyé"); Assert.That((Color32)f.GetComponent<MeshRenderer>().sharedMaterial.color, Is.EqualTo((Color32)(nom == "du dû" ? FlechesDeCarte.VIOLET : FlechesDeCarte.ORANGE)));
        }
        // L'alerte se lit sur les lieux servis : de près, de loin, sous une armée ou sous le nombre de ses hommes, c'est le même ensemble trié et la même version.
        [Test] public void L_alerte_ne_depend_ni_de_la_vue_ni_des_armees()
        {
            // Trois lieux du joueur en alerte, servis dans le désordre, un sans alerte ; un lieu d'un autre maître en alerte, qui ne compte pas.
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(20, 0)); var guerre = racine.GetComponent<CarteDeLaGuerre>(); var calques = racine.GetComponent<CalquesCarte>();
            Servir(cell => LectureLieu.De(cell == 10 ? Cellule(10, 3, Place(10, 2, 81000, 2000, JOUEUR, 7, 2), Place(10, 1, 41000, 2000, JOUEUR, 1, 2), Place(10, 0, 1000, 2000, JOUEUR, 9, 2)) : Cellule(20, 3, Place(20, 1, 61000, 2000, B, 9, 2), Place(20, 0, 21000, 2000, JOUEUR, 3, 1))));
            Assert.That(Alertes(), Is.EqualTo("10-0,10-2,20-0")); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(1));
            void Inchange(string vue) { Assert.That(Alertes(), Is.EqualTo("10-0,10-2,20-0"), vue); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(1), vue); Assert.That(Posees(), Is.Empty, vue); }
            foreach (float demi in new[] { 60f, 1000f, 2000f }) { Voir(demi); Inchange("demi " + demi + " km"); }
            // L'armée arrive sur un lieu : sa figurine et le nombre de ses hommes ne cachent aucune alerte.
            Armees(guerre, calques, new ArmeeLue(0, JOUEUR, 10, 0, 1200, 500, 10L, null, new long[0], new PointCarte(81000, 2000), new PointCarte[0])); Voir(1000); Assert.That(calques.PlacesDesNombres, Has.Count.EqualTo(1), "échantillon vide : le nombre de l'armée n'est pas montré"); Inchange("sous l'armée");
            // Une relecture identique garde la version ; un lieu de moins en alerte la change.
            Servir(cell => LectureLieu.De(cell == 10 ? Cellule(10, 4, Place(10, 2, 81000, 2000, JOUEUR, 7, 2), Place(10, 1, 41000, 2000, JOUEUR, 1, 2), Place(10, 0, 1000, 2000, JOUEUR, 9, 2)) : Cellule(20, 4, Place(20, 1, 61000, 2000, B, 9, 2), Place(20, 0, 21000, 2000, JOUEUR, 3, 1)))); Inchange("relecture identique");
            Servir(cell => LectureLieu.De(cell == 10 ? Cellule(10, 5, Place(10, 2, 81000, 2000, JOUEUR, 7, 2), Place(10, 1, 41000, 2000, JOUEUR, 1, 2), Place(10, 0, 1000, 2000, JOUEUR, 9, 2)) : Cellule(20, 5, Place(20, 1, 61000, 2000, B, 9, 2), Place(20, 0, 21000, 2000, JOUEUR, 1, 3))));
            Assert.That(Alertes(), Is.EqualTo("10-0,10-2")); Assert.That(lieux.VersionDesAlertes, Is.EqualTo(2));
        }
        // La caméra témoin regarde d'en haut le point (41000, 2000) : `demi` km de part et d'autre sur un écran de 900 pixels de haut, et les armées s'y règlent.
        const int ECRAN_PX = 900; RenderTexture ecran;
        void Voir(float demi)
        {
            if (ecran == null) { ecran = new RenderTexture(1600, ECRAN_PX, 16); camera.targetTexture = ecran; camera.orthographic = true; }
            camera.transform.SetPositionAndRotation(carte.PositionSurLaCarte(new PointCarte(41000, 2000), 0f).Value + Vector3.up * 100f, Quaternion.Euler(90, 0, 0)); camera.orthographicSize = demi;
            // Dans l'ordre d'une image : les armées et leurs nombres se règlent sur la vue, puis les étiquettes se posent.
            racine.GetComponent<CarteDeLaGuerre>().SuivreLaVue(); var calques = racine.GetComponent<CalquesCarte>(); Peindre(calques); Peindre(calques);
        }
        static void Peindre(CalquesCarte calques) => typeof(CalquesCarte).GetMethod("LateUpdate", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic).Invoke(calques, null);
        // Les armées que la carte de la guerre lit et pose, sur la terre 10 tenue par le joueur.
        void Armees(CarteDeLaGuerre guerre, CalquesCarte calques, params ArmeeLue[] armees)
        {
            guerre.LecteurTerres = () => Lecture<TerresDeLaCarte>.De(new TerresDeLaCarte(5, new DateDuMonde(1400, 6), new[] { new PaysDeLaCarte("a", "Avalon") }, new[] { new TerreLue(10, JOUEUR, "a") }));
            guerre.LecteurGuerres = () => Lecture<GuerresLues>.De(new GuerresLues(5, new DateDuMonde(1400, 6), new GuerreLue[0], armees, new PriseLue[0], 0));
            for (int passe = 0; passe < 4; passe++)
            {
                guerre.Pas(horlogeDeGuerre); var fin = DateTime.UtcNow.AddSeconds(10); while (guerre.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5);
                Assert.That(guerre.LectureEnVol, Is.False, "lecture de la guerre encore en vol"); guerre.Pas(horlogeDeGuerre); horlogeDeGuerre += CarteDeLaGuerre.PERIODE_S;
            }
            Assert.That(guerre.NombresDesArmees.Count(n => n != null), Is.EqualTo(armees.Length), "les armées témoins ne sont pas posées : " + guerre.AbsenceDesGuerres + " " + guerre.AbsenceDesTerres);
        }
        double horlogeDeGuerre;
        // La terre 10 est posée pour de bon ; l'origine et la vue sont ensuite celles que les lieux témoins attendent.
        void Preparer() { horloge = 0; lieux = racine.GetComponent<LieuxDeCarte>(); Dessiner(10); typeof(CarteDessinee).GetField("origine", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic).SetValue(carte, (PointCarte?)new PointCarte(3000000, 1500000)); Poser(carte, "Vue", new VueDeCarte(new Bounds(Vector3.zero, new Vector3(8000f, 1f, 6000f)), 1.6f)); camera = new GameObject("caméra témoin").AddComponent<Camera>(); camera.transform.SetParent(racine.transform, false); camera.transform.position = new Vector3(3, 4, 5); carte.camera = camera; Assert.That(carte.Vue != null && carte.PositionSurLaCarte(new PointCarte(1, 1), 0f) != null, Is.True); }
        void Publier(string id, params LieuTenu[] tenus) { if (partie == null) partie = new LecturePartie(() => null, _ => null, () => null, _ => null); cabinet.Partie = partie; Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(1, new DateDuMonde(1400, 1), 0, new CelluleDuMonde[0]), id))); Poser(partie, "Maison", Lecture<MaisonLue>.De(new MaisonLue(id, "Maison", new SiegeDeMaison(tenus[0].CellId, tenus[0].Rang, "Siège", new PointCarte(1, 2)), tenus, new Dictionary<string, string>()))); }
        static void Poser(object cible, string nom, object valeur) => cible.GetType().GetProperty(nom).GetSetMethod(true).Invoke(cible, new[] { valeur });
        void Servir(Func<long, LectureLieu> lire) { lieux.Lecteur = lire; lieux.Pas(horloge); var fin = DateTime.UtcNow.AddSeconds(5); while (lieux.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5); Assert.That(lieux.LectureEnVol, Is.False, lieux.TexteLegende); lieux.Pas(horloge); horloge += LieuxDeCarte.PERIODE_S; }
        static (long, long, double, double, string)[] Attendu() => new[] { (10L, 0L, 1000d, 2000d, JOUEUR), (10L, 1L, 5000d, 2500d, B), (10L, 2L, 1500d, 7000d, C), (20L, 0L, 9000d, 1000d, B), (20L, 1L, 12000d, 4000d, JOUEUR) };
        static LectureLieu Reponse(long cell, long tick, bool inverse, long partis = 1) { var tous = Attendu().Where(p => p.Item1 == cell).Select(p => Place(cell, p.Item2, p.Item3, p.Item4, p.Item5, partis, 2)).ToArray(); if (inverse) Array.Reverse(tous); return LectureLieu.De(Cellule(cell, tick, tous)); }
        static LectureLieu Complet(long cell, long tick) => cell == 20 ? LectureLieu.De(Cellule(20, tick, Place(20, 0, 8000, 3000, JOUEUR, 2, 1))) : cell == 10 ? LectureLieu.De(Cellule(10, tick, Place(10, 0, 1000, 2000, JOUEUR, 2, 1), Place(10, 1, 4000, 2000, B, 1, 1))) : LectureLieu.Absent("cellule extérieure " + cell);
        static Lieu Cellule(long cell, long tick, params LieuPlace[] places) => new Lieu(cell, tick, 1400, (int)tick + 1, 1, new Dictionary<string, double>(), 0, 0, lieux: places); // le service sert le jour tick + 1
        static LieuPlace Place(long cell, long rang, double x, double y, string maitre, long partis, long arrives) => new LieuPlace(rang, new PointCarte(x, y), maitre, new FluxDeLieu(0, partis, arrives), nom: NomDe(cell, rang));
        static string NomDe(long cell, long rang) => (cell, rang) switch { (10, 0) => "Alba", (10, 1) => "Brivas", (10, 2) => "Cerda", (20, 0) => "Dara", (20, 1) => "Elne", _ => throw new ArgumentOutOfRangeException(nameof(rang), "aucun nom pour " + cell + "-" + rang) };
        // Les lieux en alerte, « cellule-rang » séparés par des virgules ; et ce que la lecture des lieux aurait posé sur la carte (rien).
        string Alertes() => string.Join(",", lieux.EnAlerte.Select(a => a.cell + "-" + a.rang));
        string[] Posees() => racine.GetComponentsInChildren<Transform>(true).Select(t => t.name).Where(n => n == "Lieux de la carte" || n.StartsWith("Lieu ", StringComparison.Ordinal)).ToArray();
        // Un clic gauche court garde la terre, un glisser ne choisit rien, Échap ferme le dossier avant d'ouvrir le menu.
        static readonly Vector2 O = new Vector2(400, 300);
        static CelluleDeCarte Terre(long id, string ville) => new CelluleDeCarte(id, new PolygoneDeCarte[0], new IdentiteDeCarte(1, "Puissance test"), null, new[] { new VilleDeCarte(ville, 12, new PointCarte(0, 0)) });
        // Une carte témoin posée pour de bon, sans service : une terre carrée de 10 km par numéro, d'ouest en est.
        void Dessiner(params long[] ids)
        {
            carte = racine.GetComponent<CarteDessinee>(); var lue = new CarteLue(ids.Length, ids.Select((id, rang) => Carre(id, rang * 10000d)).ToArray()); carte.Montrer(lue, new FormesLues(null, lue.Cellules.Select(c => new FormeDeCellule(c.CellId, c.Contour, new[] { new FormeDeLieu(0, c.Contour) }))));
            Assert.That(carte.CellulesPosees, Is.EqualTo(ids.Length), "la carte témoin n'est pas posée");
        }
        static CelluleDeCarte Carre(long id, double x)
        {
            var anneau = new[] { new PointCarte(x, 0), new PointCarte(x + 10000, 0), new PointCarte(x + 10000, 10000), new PointCarte(x, 10000), new PointCarte(x, 0) };
            return new CelluleDeCarte(id, new[] { new PolygoneDeCarte(anneau, new IEnumerable<PointCarte>[0]) }, null, null, new VilleDeCarte[0]);
        }
        bool Geste(CelluleDeCarte sous, params Vector2[] chemin) { bool garde = cabinet.Noter(chemin[0], true, false, false, sous); for (int i = 1; i < chemin.Length; i++) garde |= cabinet.Noter(chemin[i], false, i == chemin.Length - 1, false, sous); return garde; }
        string Territoire() => racine.GetComponentsInChildren<Text>(true).Single(t => t.transform.parent.name == "Lecture du territoire").text;
        [Test] public void UnClicSansMouvementGardeLaTerre()
        {
            Dessiner(7, 8); var sept = Terre(7, "Ville test"); Color teinte = carte.TeinteDe(7).Value; Assert.That(carte.Marquee, Is.Null);
            Assert.That(Geste(sept, O, O), Is.True); Assert.That(cabinet.Retenue, Is.SameAs(sept)); cabinet.Afficher(); racine.GetComponent<DossierTerritoire>().Pas(0);
            Assert.That(Territoire(), Does.StartWith(DossierTerritoire.PAYS_EN_LECTURE).And.Not.Contain("Clic gauche sur une terre"), "la fiche de la terre gardée ne s'écrit pas");
            Assert.That(racine.transform.Find("Cabinet/" + CabinetDeCarte.TERRITOIRE + "/" + CabinetDeCarte.TERRITOIRE).GetComponent<Text>().text, Is.EqualTo(DossierTerritoire.PROVINCE_EN_LECTURE), "le titre de la fiche ne nomme pas la province");
            // Le rang du lieu cliqué suit la terre gardée.
            cabinet.Relacher(); Assert.That(cabinet.Noter(O, true, true, false, sept, 3) && cabinet.Retenue == sept && cabinet.RangRetenu == 3, Is.True, "le lieu cliqué n'est pas gardé");
            Assert.That(carte.Marquee, Is.EqualTo(7), "la terre gardée n'est pas marquée");
            cabinet.Relacher(); Assert.That(carte.Marquee, Is.Null, "la terre relâchée reste marquée"); Assert.That(cabinet.Noter(O, true, true, false, sept) && cabinet.Retenue == sept, Is.True, "appui et relâché dans la même image");
            cabinet.Relacher(); Assert.That(Geste(sept, O, O + new Vector2(6, 0)) && cabinet.Retenue == sept, Is.True, "relâché à 6 px");
            Assert.That(carte.Marquee, Is.EqualTo(7)); Assert.That(carte.TeinteDe(7), Is.EqualTo(teinte), "la marque couvre la teinte de la terre, elle ne la change pas");
            // Une terre que la carte ne dessine pas se garde sans marque, et la marque d'avant tombe.
            var absente = Terre(9, "Ville neuve"); Assert.That(Geste(absente, O, O) && cabinet.Retenue == absente, Is.True); Assert.That(carte.Marquee, Is.Null);
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
            Dessiner(7); var menu = racine.GetComponent<MenuCabinet>(); Assert.That(Geste(Terre(7, "Ville test"), O, O) && !menu.Ouvert && carte.Marquee == 7, Is.True); cabinet.Afficher();
            menu.Echap(); cabinet.Afficher();
            Assert.That(cabinet.Retenue == null && !menu.Ouvert && carte.Marquee == null, Is.True, "le premier Échap ferme le dossier, pas plus");
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
        // « Votre maison » parle en noms et en dates.
        Text Nomme(string nom) => racine.GetComponentsInChildren<Text>(true).Single(t => t.name == nom);
        string Propre(string nom) { string t = Nomme(nom).text; Assert.That(TexteDuMonde.Interdit(t, "10340") ?? TexteDuMonde.SansUnite(t), Is.Null, t); return t; }
        [Test] public void LaMaisonDuJoueurDitSonNomSonSiegeSesLieuxEtLaDate()
        {
            Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0)); cabinet.Afficher(); Assert.That(Propre("Lecture de la partie…"), Is.EqualTo("Maison\nSiège : Siège\n3 lieux tenus · relevé au jour 1 de 1400"));
            Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); Assert.That(Propre("Lecture de la partie…"), Does.EndWith("\n1 lieu tenu · relevé au jour 1 de 1400"));
        }
        // Une fiche servie par `/jouables`, de pays « Despotat témoin » ; sa ville est bâtie ou non.
        static FicheJouable Jouable(string id, long cell, bool batie = false) => new FicheJouable(id, "Maison témoin", "seigneurie", 3, new IdentiteDePays(id, "Despotat témoin"),
            new[] { new IdentiteDePays(id, "Despotat témoin") }, new SiegeJouable("Mistra", "Mistra", cell), null,
            batie ? new VilleJouable(true, "3d/unity/Assets/Ville témoin.unity", null) : new VilleJouable(false, null, "la ville de Mistra n'est pas encore bâtie en 3D ; seule Biskra l'est"));
        static Lecture<JouablesLus> JouablesDe(params FicheJouable[] fiches) => Lecture<JouablesLus>.De(new JouablesLus(1, new DateDuMonde(1400, 1), fiches));
        static Lecture<MondeAvecMaisonLu> MondeDe(string maison) => Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(1, new DateDuMonde(1400, 1), 0, new CelluleDuMonde[0]), maison));
        // L'accueil ouvert sur un départ conseillé, puis ce départ pris dans la liste.
        void Proposer()
        {
            partie = new LecturePartie(() => null, _ => null, () => null, _ => null); cabinet.Partie = partie; Poser(partie, "Monde", MondeDe(null));
            Poser(partie, "Jouables", JouablesDe(Jouable("seigneurie-42", 10340)));
            cabinet.Afficher(); racine.GetComponentsInChildren<Button>(true).Single(b => b.name == "Despotat témoin").onClick.Invoke(); cabinet.Afficher();
        }
        static HorlogeLue Horloge(double joursParSeconde) => new HorlogeLue(7, new DateDuMonde(1400, 8), joursParSeconde);
        // Le choix accepté ne lance pas le temps : l'horloge reste en pause, rien ne lui est demandé, et « Pause / Reprendre » porte
        // l'engagement du socle (comme « Commencer ») tant que le monde attend ; la date dit « En pause » et le guide dit quoi faire.
        [Test] public async System.Threading.Tasks.Task Apres_le_choix_le_temps_reste_en_pause_et_sa_commande_est_mise_en_avant()
        {
            partie = new LecturePartie(() => null, _ => null, () => null, _ => RecuIntention.AccepteeAu(7)); cabinet.Partie = partie; Poser(partie, "Monde", MondeDe(null));
            Poser(partie, "Jouables", JouablesDe(Jouable("seigneurie-42", 10340)));
            var horloge = racine.GetComponent<HorlogeDeCarte>(); Poser(horloge, "Lue", Horloge(0));
            var bouton = racine.GetComponentsInChildren<Button>(true).Single(b => b.name == "Pause / Reprendre"); var ordinaire = bouton.colors.normalColor;
            cabinet.Afficher(); racine.GetComponentsInChildren<Button>(true).Single(b => b.name == "Despotat témoin").onClick.Invoke(); cabinet.Afficher();
            Assert.That(cabinet.TempsMisEnAvant, Is.False, "le temps est mis en avant avant le choix");
            await cabinet.Accueil.Lancer(); cabinet.Afficher();
            Assert.That(partie.Recu?.Acceptee, Is.True, "le choix n'est pas reçu : échantillon vide");
            // Le monde en pause n'a pas encore joué le jour qui applique le choix : l'accueil est déjà fermé et la barre nomme le pays choisi.
            Assert.That(cabinet.Accueil.Ouvert, Is.False, "l'accueil reste ouvert après le reçu"); Assert.That(cabinet.Accueil.Panneau.gameObject.activeSelf, Is.False);
            Assert.That(Propre(BARRE), Is.EqualTo("Despotat témoin · choix reçu, le monde l'applique à son premier jour"));
            var demandee = typeof(HorlogeDeCarte).GetField("vitesseDemandee", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            Assert.That(demandee.GetValue(horloge), Is.Null, "le choix a demandé une vitesse à l'horloge"); Assert.That(horloge.EnPause, Is.True);
            Assert.That(cabinet.TempsMisEnAvant, Is.True, "« Pause / Reprendre » n'est pas mis en avant après le choix");
            Assert.That(bouton.colors.normalColor, Is.EqualTo(SocleInterface.Couleur("alerte")), "la matière d'engagement n'est pas posée");
            Assert.That(bouton.GetComponentInChildren<Text>().text, Is.EqualTo("Reprendre"));
            Assert.That(Nomme(CabinetDeCarte.GUIDE).text, Is.EqualTo(CabinetDeCarte.CHOIX_RECU));
            Assert.That(racine.GetComponentsInChildren<Text>().Any(t => t.text == HorlogeDeCarte.Decrire(Horloge(0)) && t.text.EndsWith("En pause")), Is.True, "la date ne dit pas « En pause »");
            // Le temps lancé, la commande redevient ordinaire ; la maison servie et le monde remis en pause, elle revient.
            Poser(horloge, "Lue", Horloge(6)); cabinet.Afficher();
            Assert.That(cabinet.TempsMisEnAvant || bouton.colors.normalColor != ordinaire, Is.False, "la commande reste mise en avant quand le temps file");
            Publier(JOUEUR, new LieuTenu(10, 0)); Poser(horloge, "Lue", Horloge(0)); cabinet.Afficher(); Assert.That(cabinet.TempsMisEnAvant, Is.True, "la maison servie en pause n'appelle pas le temps");
            // Contre-épreuve : basculer l'horloge, ce que faisait le choix, lui demande bien une vitesse.
            horloge.Basculer(); Assert.That(demandee.GetValue(horloge), Is.Not.Null);
        }
        [Test] public void La_ligne_du_prochain_geste_suit_la_partie()
        {
            Assert.That(CabinetDeCarte.CHOISIR, Is.EqualTo("Choisissez votre pays, puis « Commencer »"));
            Assert.That(CabinetDeCarte.CHOIX_RECU, Is.EqualTo("Choix reçu · En pause : « Reprendre » lance le temps"));
            Assert.That(CabinetDeCarte.LANCER, Is.EqualTo("En pause : « Reprendre » lance le temps"));
            string Guide(Lecture<MondeAvecMaisonLu> monde, Lecture<JouablesLus> jouables, RecuIntention recu, HorlogeLue h, bool ville = false) => CabinetDeCarte.Guide(monde, jouables, recu, h, ville);
            var jouables = JouablesDe(Jouable("seigneurie-42", 10340)); var sans = MondeDe(null); var avec = MondeDe(JOUEUR); var recu = RecuIntention.AccepteeAu(7);
            Assert.That(Guide(null, jouables, null, Horloge(0)), Is.Null); Assert.That(Guide(Lecture<MondeAvecMaisonLu>.Absent("panne"), jouables, null, Horloge(0)), Is.Null);
            Assert.That(Guide(sans, jouables, null, null), Is.EqualTo(CabinetDeCarte.CHOISIR)); Assert.That(Guide(sans, jouables, null, Horloge(6)), Is.EqualTo(CabinetDeCarte.CHOISIR), "même si le temps file");
            Assert.That(Guide(sans, null, null, Horloge(0)), Is.Null); Assert.That(Guide(sans, Lecture<JouablesLus>.Absent("panne"), null, Horloge(0)), Is.Null);
            Assert.That(Guide(sans, jouables, recu, Horloge(0)), Is.EqualTo(CabinetDeCarte.CHOIX_RECU));
            Assert.That(Guide(sans, jouables, recu, null), Is.Null); Assert.That(Guide(sans, jouables, recu, Horloge(6)), Is.Null);
            Assert.That(Guide(sans, jouables, RecuIntention.Refusee(409, "refus"), Horloge(0)), Is.EqualTo(CabinetDeCarte.CHOISIR));
            Assert.That(Guide(avec, null, null, Horloge(0)), Is.EqualTo(CabinetDeCarte.LANCER));
            Assert.That(Guide(avec, null, null, Horloge(0), true), Is.EqualTo(CabinetDeCarte.LANCER + CabinetDeCarte.ENTRER));
            Assert.That(Guide(avec, null, null, null), Is.Null); Assert.That(Guide(avec, null, null, Horloge(6), true), Is.Null);
            foreach (var phrase in new[] { CabinetDeCarte.CHOISIR, CabinetDeCarte.CHOIX_RECU, CabinetDeCarte.LANCER, CabinetDeCarte.LANCER + CabinetDeCarte.ENTRER })
            {
                Assert.That(TexteDuMonde.Interdit(phrase, "10340", "42") ?? TexteDuMonde.SansUnite(phrase), Is.Null, phrase);
                Assert.That(phrase, Does.Not.Contain("Espace").And.Not.Contain("double-clic").And.Not.Contain("Échap"), "la ligne nomme une touche : " + phrase);
            }

            var texte = Nomme(CabinetDeCarte.GUIDE); var rect = texte.rectTransform;
            Assert.That(texte.transform.parent.name, Is.EqualTo("FORGE · Le cabinet")); Assert.That(rect.anchoredPosition, Is.EqualTo(new Vector2(1104, -72))); Assert.That(rect.sizeDelta, Is.EqualTo(new Vector2(792, 26)));
            Assert.That(texte.alignment, Is.EqualTo(TextAnchor.MiddleRight)); Assert.That(texte.raycastTarget, Is.False);
            texte.text = CabinetDeCarte.LANCER + CabinetDeCarte.ENTRER; Assert.That(texte.preferredWidth, Is.LessThanOrEqualTo(792f), "la plus longue phrase déborde de sa ligne");
            var horloge = racine.GetComponent<HorlogeDeCarte>();
            Proposer(); Assert.That(texte.gameObject.activeSelf, Is.True); Assert.That(texte.text, Is.EqualTo(CabinetDeCarte.CHOISIR));
            Poser(partie, "Recu", RecuIntention.AccepteeAu(7));
            Poser(horloge, "Lue", new HorlogeLue(7, new DateDuMonde(1400, 8), 0)); cabinet.Afficher(); Assert.That(texte.gameObject.activeSelf && texte.text == CabinetDeCarte.CHOIX_RECU, Is.True, texte.text);
            // La maison servie : la ligne dit d'entrer dans la ville seulement si sa fiche jouable la dit bâtie.
            Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); Assert.That(texte.gameObject.activeSelf && texte.text == CabinetDeCarte.LANCER, Is.True, texte.text);
            Poser(partie, "Jouables", JouablesDe(Jouable(JOUEUR, 10, true))); cabinet.Afficher(); Assert.That(texte.text, Is.EqualTo(CabinetDeCarte.LANCER + CabinetDeCarte.ENTRER), "la capitale servie est bâtie");
            Poser(partie, "Jouables", JouablesDe(Jouable(JOUEUR, 10))); cabinet.Afficher(); Assert.That(texte.text, Is.EqualTo(CabinetDeCarte.LANCER));
            Poser(horloge, "Lue", new HorlogeLue(7, new DateDuMonde(1400, 8), 6)); cabinet.Afficher(); Assert.That(texte.gameObject.activeSelf, Is.False, "le temps file : la ligne se tait");
            Poser(partie, "Monde", null); cabinet.Afficher(); Assert.That(texte.gameObject.activeSelf, Is.False, "sans monde, la ligne se tait");
            foreach (var enfant in racine.GetComponentsInChildren<Button>().Where(b => b.transform.parent.name == "FORGE · Le cabinet")) Assert.That(enfant.name, Is.Not.EqualTo(CabinetDeCarte.GUIDE));
        }

        [Test] public void Les_terres_conseillees_s_eclairent_et_un_clic_montre_leur_pays()
        {
            // La carte dessine les terres 10340 et 77 ; la fiche 43 conseille une terre (9999) qu'elle ne dessine pas.
            Dessiner(10340, 77); Color teinte = carte.TeinteDe(10340).Value; Material terrain = racine.transform.Find(CarteDessinee.TERRAIN).GetComponent<MeshRenderer>().sharedMaterial;
            partie = new LecturePartie(() => null, _ => null, () => null, _ => null); cabinet.Partie = partie; Poser(partie, "Monde", MondeDe(null)); Poser(partie, "Jouables", JouablesDe(Jouable("seigneurie-42", 10340), Jouable("seigneurie-43", 9999)));
            cabinet.Afficher();
            // La surbrillance n'est pas un maillage plat posé au-dessus du terrain, qui cacherait le relief et que les montagnes
            // traverseraient : c'est le terrain lui-même qui s'éclaire, à l'or du socle.
            long[] Eclairees() => new long[] { 10340, 77, 9999 }.Where(c => carte.EclatDe(c).HasValue).ToArray();
            Assert.That(Eclairees(), Is.EqualTo(new[] { 10340L }), "une surbrillance par départ conseillé dont la carte dessine le siège");
            Color or = SocleInterface.Couleur("or"); or.a = 1f; Assert.That((Color32)carte.EclatDe(10340).Value, Is.EqualTo((Color32)or));
            Assert.That(racine.GetComponentsInChildren<MeshFilter>(true).Count(f => f.name != CarteDessinee.TERRAIN), Is.Zero, "la surbrillance pose un maillage au-dessus du terrain");
            Assert.That(racine.transform.Find(CarteDessinee.TERRAIN).GetComponent<MeshRenderer>().sharedMaterial, Is.SameAs(terrain));
            Assert.That(carte.TeinteDe(10340), Is.EqualTo(teinte), "la surbrillance couvre la teinte de la terre, elle ne la change pas"); Assert.That(carte.Marquee, Is.Null);
            cabinet.Afficher(); Assert.That(Eclairees(), Is.EqualTo(new[] { 10340L }), "un second Afficher éteint ou déplace la surbrillance");

            Button commencer = racine.GetComponentsInChildren<Button>(true).Single(b => b.name == AccueilDuPays.COMMENCER);
            Assert.That(commencer.interactable, Is.False, "sans pays choisi, « Commencer » est inactif");
            Assert.That(Geste(Terre(10340, "Ville test"), O, O), Is.True); cabinet.Afficher();
            Assert.That(carte.Marquee, Is.EqualTo(10340), "la terre gardée garde son rouge : la marque passe devant l'éclat");
            Assert.That(cabinet.Accueil.Montree.Id, Is.EqualTo("seigneurie-42"), "le siège cliqué montre son pays"); Assert.That(cabinet.Accueil.TexteDuNom, Is.EqualTo("Despotat témoin"));
            Assert.That(commencer.interactable, Is.True);
            cabinet.Relacher(); cabinet.Afficher(); Assert.That(Eclairees(), Is.EqualTo(new[] { 10340L })); Assert.That(carte.Marquee, Is.Null); Assert.That(cabinet.Accueil.Montree.Id, Is.EqualTo("seigneurie-42"));
            Assert.That(Geste(Terre(77, "Ville sans fiche"), O, O), Is.True); cabinet.Afficher(); Assert.That(cabinet.Accueil.Montree.Id, Is.EqualTo("seigneurie-42"), "une terre sans pays ne change pas le pays montré");
            Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); Assert.That(Eclairees(), Is.Empty, "une maison choisie : plus de terre éclairée");
            Assert.That(cabinet.Accueil.Ouvert, Is.False); Assert.That(cabinet.Accueil.Panneau.gameObject.activeSelf, Is.False, "l'accueil se ferme quand la maison est servie");
            Poser(partie, "Monde", MondeDe(null)); cabinet.Afficher(); Assert.That(cabinet.Accueil.Ouvert, Is.False, "l'accueil ne revient pas"); Assert.That(Eclairees(), Is.Empty);
        }

        // Tant que l'accueil est ouvert, il se tient à la place de « Votre maison » et de la fiche de la terre, qu'il cache, sans laisser l'ancien choix.
        // Quand la maison du joueur est servie, la vue se pose une fois sur son siège ; le joueur la mène ensuite.
        [Test] public void La_carte_se_centre_une_fois_sur_le_siege_de_la_maison_servie()
        {
            Preparer(); partie = new LecturePartie(() => null, _ => null, () => null, _ => null); cabinet.Partie = partie;
            void Servir(string id, PointCarte siege)
            {
                Poser(partie, "Monde", MondeDe(id));
                Poser(partie, "Maison", Lecture<MaisonLue>.De(new MaisonLue(id, "Maison", new SiegeDeMaison(10, 0, "Siège", siege), new[] { new LieuTenu(10, 0) }, new Dictionary<string, string>())));
                cabinet.Afficher();
            }
            Vector2 Attendu(PointCarte p) { Vector3 ici = carte.PositionSurLaCarte(p, 0f).Value; return new Vector2(ici.x, ici.z); }
            var avant = carte.Vue.Centre; Poser(partie, "Monde", MondeDe(null)); cabinet.Afficher(); Assert.That(carte.Vue.Centre, Is.EqualTo(avant), "la vue bouge sans maison");
            var siege = new PointCarte(3001000, 1502000); Servir(JOUEUR, siege);
            Assert.That(Vector2.Distance(carte.Vue.Centre, Attendu(siege)), Is.LessThan(1e-3f), "la vue ne vise pas le siège : " + carte.Vue.Centre);
            Assert.That(carte.Vue.Demi, Is.EqualTo(CabinetDeCarte.DEMI_SUR_LE_SIEGE_KM).Within(1e-3f));
            Assert.That(camera.transform.position, Is.EqualTo(carte.Vue.Position), "la caméra n'est pas posée sur la vue");
            carte.Vue.Centrer(new Vector2(-500, 300), 900); cabinet.Afficher(); Assert.That(carte.Vue.Centre, Is.EqualTo(new Vector2(-500, 300)), "la vue est reprise au joueur à chaque image");
            var autre = new PointCarte(2999000, 1499000); Servir(B, autre); Assert.That(Vector2.Distance(carte.Vue.Centre, Attendu(autre)), Is.LessThan(1e-3f), "une autre maison ne recentre pas");
        }

        // Le bandeau tient le haut de l'écran, l'accueil sa droite tant qu'il est ouvert : la vue de la carte ne compte que le
        // reste, en parts de la fenêtre ; la toile s'échelonne sur la largeur de l'écran.
        [Test] public void La_vue_de_la_carte_connait_la_partie_que_l_interface_lui_laisse()
        {
            void Egal(Rect attendu, Rect lu, string quand) => Assert.That(Mathf.Abs(lu.xMin - attendu.xMin) + Mathf.Abs(lu.yMin - attendu.yMin) + Mathf.Abs(lu.width - attendu.width) + Mathf.Abs(lu.height - attendu.height), Is.LessThan(1e-5f), quand + " : " + lu);
            Egal(new Rect(0, 0, 1312f / 1920f, 956f / 1080f), CabinetDeCarte.PartieLibre(new Vector2(1920, 1080), 124, 1312), "en 1920 × 1080, l'accueil ouvert");
            Egal(new Rect(0, 0, 1, 956f / 1080f), CabinetDeCarte.PartieLibre(new Vector2(3840, 2160), 124, null), "en 3840 × 2160, l'accueil fermé");
            Egal(new Rect(0, 0, 1312f / 1920f, 1f - 124f * (1280f / 1920f) / 1024f), CabinetDeCarte.PartieLibre(new Vector2(1280, 1024), 124, 1312), "en 1280 × 1024, le bandeau garde sa part de la largeur");
            Preparer(); var texture = new RenderTexture(1920, 1080, 16); camera.targetTexture = texture;
            try
            {
                Proposer(); Assert.That(cabinet.Accueil.Ouvert, Is.True, "échantillon vide : l'accueil n'est pas ouvert");
                Egal(new Rect(0, 0, 1312f / 1920f, 956f / 1080f), carte.Vue.Libre, "l'accueil ouvert, la vue ne connaît pas sa partie libre");
                Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); Assert.That(cabinet.Accueil.Ouvert, Is.False);
                Egal(new Rect(0, 0, 1, 956f / 1080f), carte.Vue.Libre, "l'accueil fermé, la vue ne reprend pas la largeur");
                Assert.That(camera.transform.position, Is.EqualTo(carte.Vue.Position), "la caméra n'est pas posée sur la vue");
            }
            finally { camera.targetTexture = null; Object.DestroyImmediate(texture); }
        }

        [Test] public void L_accueil_remplace_les_deux_dossiers_et_l_ancien_choix()
        {
            Proposer(); Transform toile = racine.transform.Find("Cabinet");
            var accueil = (RectTransform)toile.Find(AccueilDuPays.TITRE); Assert.That(accueil, Is.Not.Null); Assert.That(accueil.gameObject.activeSelf, Is.True);
            Assert.That(accueil.anchoredPosition, Is.EqualTo(new Vector2(1312, -124))); Assert.That(accueil.sizeDelta, Is.EqualTo(new Vector2(584, 932)));
            foreach (var nom in new[] { "Votre maison", "Territoire conservé" }) Assert.That(toile.Find(nom).gameObject.activeSelf, Is.False, nom + " reste visible sous l'accueil");
            foreach (var ancien in new[] { "Choisir cette maison", "Maison témoin", "Maisons proposées", "Consultez une maison avant de vous engager." })
                Assert.That(toile.GetComponentsInChildren<Transform>(true).Where(t => t.name == ancien), Is.Empty, "l'ancien choix reste : " + ancien);
            Assert.That(System.IO.File.ReadAllText("Assets/Interface/CabinetDeCarte.cs"), Does.Not.Contain("PassageALaCapitale").And.Not.Contain("SiegeLu"));
        }

        // Chaque commande du cabinet déclare sa phrase, et le cabinet la montre au survol.
        [Test] public void ChaqueCommandeDuCabinetDitCeQuElleFait()
        {
            Proposer(); Transform toile = racine.transform.Find("Cabinet"); Button[] boutons = toile.GetComponentsInChildren<Button>(true);
            var attendues = new[] { "Ralentir", "Pause / Reprendre", "Accélérer", AccueilDuPays.COMMENCER, "Despotat témoin", "Prélèvement", "Ouvrir le grenier", "Préparer", "Confirmer l’ordre",
                "Annuler / Retour", "Annuler / Retour", "Menu", "Revenir au jeu", "Politique", "Population", "Autres maisons", "Plan du bourg", "Fermer", "Chantiers",
                "Tracer une rue", "Relire le tracé", "Confirmer la rue", "Terres et comptes", "Fermer", "Fermer", "Fermer", "Votre maison", CabinetDeCarte.CAPITALE, "Fermer", "Fermer" };
            Assert.That(attendues.Length == 30 && attendues.Distinct().Count() == 24, Is.True);
            foreach (var nom in attendues.GroupBy(n => n)) Assert.That(boutons.Count(b => b.name == nom.Key), Is.GreaterThanOrEqualTo(nom.Count()), "commande absente du cabinet : " + nom.Key);
            Assert.That(boutons.Length, Is.GreaterThanOrEqualTo(30));
            foreach (var fermer in boutons.Where(b => b.name == "Fermer")) Assert.That(SocleInterfaceTests.CroixDe((RectTransform)fermer.transform.parent), Is.SameAs(fermer), "« Fermer » de « " + fermer.transform.parent.name + " » n'est pas la croix du socle");
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
            foreach (var nom in new[] { "Ralentir", "Pause / Reprendre", "Accélérer", "Menu", "Terres et comptes", "Despotat témoin", AccueilDuPays.COMMENCER, "Politique", "Population", "Autres maisons" })
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
        // L'infobulle d'un lieu dit d'abord son pays, puis le lieu, sa province et son seigneur, et n'efface pas la phrase d'un bouton.
        static DocumentDuMonde DocTerre(long cell, string nom, int tick = 8, int jour = 9) => new DocumentDuMonde("{\"tick\":" + tick + ",\"cell_id\":" + cell + ",\"date\":{\"annee\":1400,\"jour_de_l_annee\":" + jour + "},\"population\":12345,\"noms\":{\"maisons\":{\"grande-60\":{\"nom\":\"Wittelsbach-Straubing\",\"prenom_chef\":null,\"sorte\":\"grande maison\"}}},\"lieux\":[{\"rang\":0,\"nom\":\"" + nom + "\",\"population\":12000,\"surface_km2\":12,\"maitre\":\"grande-60\",\"stocks\":{\"nourriture\":1234.5},\"flux_30j\":null}]}");
        static async System.Threading.Tasks.Task Fin(LectureDossier lecture) { for (int i = 0; i < 40 && lecture.EnCours; i++) await System.Threading.Tasks.Task.Yield(); Assert.That(lecture.EnCours, Is.False, lecture.Cle); }
        async System.Threading.Tasks.Task<(InfobulleDeTerre bulle, CelluleDeCarte terre)> Montrer20()
        {
            var bulle = racine.GetComponent<InfobulleDeTerre>(); bulle.automatique = true; var terre = Terre(20, "Bourg témoin"); bulle.Terres = DossierTerritoireTests.Terres;
            var porte = new System.Threading.Tasks.TaskCompletionSource<DocumentDuMonde>(); bulle.Lecture = new LectureDossier(_ => porte.Task);
            bulle.Pas(O, terre, 0); porte.SetResult(DocTerre(20, "Bourg témoin")); await Fin(bulle.Lecture); bulle.Pas(O, terre, 0.5);
            Assert.That(bulle.TexteAffiche, Does.StartWith("Hainaut · ")); return (bulle, terre);
        }
        [Test] public async System.Threading.Tasks.Task LInfobulleDUnLieuDitSonPaysPuisLeLieuSaProvinceEtSonSeigneur()
        {
            Assert.That(racine.GetComponents<InfobulleDeTerre>(), Has.Length.EqualTo(1)); cabinet.Construire(); Assert.That(racine.GetComponents<InfobulleDeTerre>(), Has.Length.EqualTo(1));
            var bulle = racine.GetComponent<InfobulleDeTerre>(); bulle.automatique = true; var chemins = new System.Collections.Generic.List<string>(); var portes = new System.Collections.Generic.List<System.Threading.Tasks.TaskCompletionSource<DocumentDuMonde>>();
            bulle.Lecture = new LectureDossier(chemin => { chemins.Add(chemin); var porte = new System.Threading.Tasks.TaskCompletionSource<DocumentDuMonde>(); portes.Add(porte); return porte.Task; });
            bulle.Terres = () => null; string attente = DossierTerritoire.PAYS_EN_LECTURE + "\n" + DossierTerritoire.ATTENTE;
            var t10 = Terre(10, "Bourg dix"); var t20 = Terre(20, "Bourg témoin"); bulle.Pas(O, t10, 0);
            Assert.That(chemins, Is.EqualTo(new[] { "/lieu?cell=10" })); Assert.That(bulle.TexteAffiche, Is.EqualTo(attente));
            bulle.Pas(O, t20, 0.1); Assert.That(chemins, Has.Count.EqualTo(1)); Assert.That(bulle.TexteAffiche, Is.EqualTo(attente));
            portes[0].SetResult(DocTerre(10, "Bourg dix")); await Fin(bulle.Lecture); bulle.Pas(O, t20, 0.2);
            Assert.That(chemins, Is.EqualTo(new[] { "/lieu?cell=10", "/lieu?cell=20" })); Assert.That(bulle.TexteAffiche, Is.EqualTo(attente)); Assert.That(bulle.TexteAffiche, Does.Not.Contain("Bourg dix").And.Not.Contain("Dossier incomplet"));
            var doc20 = DocTerre(20, "Bourg témoin"); portes[1].SetResult(doc20); await Fin(bulle.Lecture); bulle.Pas(O, t20, 0.5);
            Assert.That(bulle.TexteAffiche, Does.StartWith(DossierTerritoire.PAYS_EN_LECTURE + "\nBourg témoin : "), "le lieu attend les terres");
            // Les terres lues : le pays du lieu passe devant, le seigneur local vient en dernier.
            bulle.Terres = DossierTerritoireTests.Terres; bulle.Pas(O, t20, 0.6);
            string attendu = "Hainaut · Saint-Empire · " + TexteDuMonde.Nombre(250000) + " habitants\nBourg témoin : " + TexteDuMonde.Nombre(12000)
                + " habitants dans ce lieu\nProvince de Bourg témoin · " + TexteDuMonde.Nombre(12345) + " habitants\nSeigneur : maison Wittelsbach-Straubing";
            Assert.That(bulle.TexteAffiche, Is.EqualTo(attendu)); Assert.That(bulle.TexteAffiche, Does.Not.Contain("jour 9").And.Not.Contain("Maison").And.Not.Contain("dans le territoire"));
            var toile = racine.transform.Find("Cabinet"); var feuillets = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray();
            Assert.That(feuillets.Length, Is.EqualTo(1)); Assert.That(feuillets[0].GetComponentInChildren<Text>().text, Is.EqualTo(attendu));
            int n = chemins.Count; bulle.Pas(O, t20, 1); Assert.That(chemins, Has.Count.EqualTo(n)); bulle.Pas(O, t20, 2.3); Assert.That(chemins, Is.EqualTo(new[] { "/lieu?cell=10", "/lieu?cell=20", "/lieu?cell=20" }));
        }
        // Le lieu survolé, pas sa terre : dans la terre partagée de Pampelune, le lieu castillan dit la Castille ; une terre sans pays dit qu'on ne la joue pas.
        [Test] public void LInfobulleParleAuGrainDuLieu()
        {
            var terres = DossierTerritoireTests.Terres(); var pampelune = DossierTerritoireTests.Lieu(DossierTerritoireTests.PAMPELUNE, "Pampelune");
            Assert.That(InfobulleDeTerre.Decrire(null, pampelune, terres, DossierTerritoireTests.PAMPELUNE, 2), Does.StartWith("Castille · ").And.Contain("\nHameau témoin : ").And.Contain("\nProvince de Pampelune · partagée : Navarre et Castille · ").And.EndWith(DossierTerritoire.SEIGNEUR_LOCAL));
            Assert.That(InfobulleDeTerre.Decrire(null, pampelune, terres, DossierTerritoireTests.PAMPELUNE, 0), Does.StartWith("Navarre · ").And.EndWith("Seigneur : maison Wittelsbach-Straubing"));
            Assert.That(InfobulleDeTerre.Decrire(null, DossierTerritoireTests.Lieu(DossierTerritoireTests.BORDEAUX, "Bordeaux"), terres, DossierTerritoireTests.BORDEAUX, 0), Does.StartWith("Guyenne · vassal d'Angleterre · "));
            Assert.That(InfobulleDeTerre.Decrire(null, DossierTerritoireTests.Lieu(DossierTerritoireTests.AVIGNON, "Avignon"), terres, DossierTerritoireTests.AVIGNON, 0), Does.StartWith("États de l'Église · ").And.Not.Contain("vassal"));
            Assert.That(InfobulleDeTerre.Decrire(null, DossierTerritoireTests.Lieu(DossierTerritoireTests.SANS_PAYS, "Bourg libre"), terres, DossierTerritoireTests.SANS_PAYS, 0), Does.StartWith(DossierTerritoire.SANS_ETAT + " · " + DossierTerritoire.AUCUN_PAYS + " · " + DossierTerritoire.ON_NE_LA_JOUE_PAS + "\n"));
            Assert.That(InfobulleDeTerre.Decrire(null, DossierTerritoireTests.Lieu(DossierTerritoireTests.DESERT, "Le Souf"), terres, DossierTerritoireTests.DESERT, 0), Does.StartWith("Terre sans État · Tribus du désert · on ne la joue pas\n"));
            // Le rang survolé passe à l'infobulle, qui se récrit quand il change sans changer de terre.
            var bulle = racine.GetComponent<InfobulleDeTerre>(); bulle.automatique = true; bulle.Terres = () => terres;
            bulle.Lecture = new LectureDossier(_ => System.Threading.Tasks.Task.FromResult(pampelune)); var terre = Terre(DossierTerritoireTests.PAMPELUNE, "Pampelune");
            var ici = new Vector2(620, 300); // à droite de l'écran de test : le feuillet du lieu, plus large, se pose à sa gauche
            bulle.Pas(ici, terre, 0, 2); for (int i = 0; i < 40 && bulle.Lecture.EnCours; i++) System.Threading.Thread.Sleep(5); bulle.Pas(ici, terre, 0.1, 2);
            Assert.That(bulle.TexteAffiche, Does.StartWith("Castille · ")); bulle.Pas(ici, terre, 0.2, 0); Assert.That(bulle.TexteAffiche, Does.StartWith("Navarre · "));
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
            bulle.Pas(O, terre, 1); Assert.That(bulle.TexteAffiche, Does.StartWith("Hainaut · ")); bulle.Pas(O, null, 1);
            Assert.That(toile.GetComponentsInChildren<RectTransform>().Any(t => t.name == "Infobulle"), Is.False); Assert.That(racine.GetComponentsInChildren<Canvas>().Length, Is.EqualTo(1));
        }
        // L'infobulle d'une terre ajoute, au même tick, les lignes de `/modificateurs` pour son bourg ; elle les lit, elle ne les calcule pas.
        const string POSE_MOULIN = "{\"nom\":\"Moulin\",\"source\":\"batiment:moulin-paris\",\"valeur\":0.1,\"source_dite\":\"bâtiment\",\"reste_jours\":null}";
        const string POSE_IDEE = "{\"nom\":\"Assolement triennal\",\"source\":\"idee:assolement\",\"valeur\":0.0196,\"source_dite\":\"idée\",\"reste_jours\":null}";
        const string POSE_EPREUVE = "{\"nom\":\"Épreuve de l'infobulle\",\"source\":\"evenement:epreuve-de-l-infobulle\",\"valeur\":-0.05,\"source_dite\":\"événement\",\"reste_jours\":90}";
        static string Lieu(long cell, int rang, string grandeurs) => "{\"cell_id\":" + cell + ",\"rang\":" + rang + ",\"grandeurs\":{" + grandeurs + "}}";
        static string Grandeur(string id, string nom, double total, params string[] poses) => "\"" + id + "\":{\"nom\":\"" + nom + "\",\"total\":" + total.ToString(System.Globalization.CultureInfo.InvariantCulture) + ",\"facteur\":1,\"lignes\":[" + string.Join(",", poses) + "]}";
        static DocumentDuMonde DocModificateurs(int tick, params string[] lieux) => new DocumentDuMonde("{\"tick\":" + tick + ",\"date\":{\"annee\":1400,\"jour_de_l_annee\":9},\"poses\":[],\"lieux\":[" + string.Join(",", lieux) + "]}");
        // Trois poses sur deux grandeurs au bourg de 20 ; un champ (rang 1) de 20 et le bourg de 30 portent aussi des poses, qui ne doivent pas se lire.
        static DocumentDuMonde TroisPoses(int tick = 8) => DocModificateurs(tick,
            Lieu(30, 0, Grandeur("departs", "Départs", 0.1, POSE_MOULIN)), Lieu(20, 1, Grandeur("commerce", "Commerce", 0.1, POSE_MOULIN)),
            Lieu(20, 0, Grandeur("natalite", "Natalité", -0.05, POSE_EPREUVE) + "," + Grandeur("recolte", "Récolte", 0.1196, POSE_MOULIN, POSE_IDEE)));
        static readonly string[] LIGNES_ATTENDUES = { "Natalité : -5 % Épreuve de l'infobulle · événement · encore 90 jours", "Natalité, total : -5 %",
            "Récolte : +10 % Moulin · bâtiment · tant que sa source tient", "Récolte : +1,96 % Assolement triennal · idée · tant que sa source tient", "Récolte, total : +11,96 %" };
        async System.Threading.Tasks.Task<(InfobulleDeTerre bulle, CelluleDeCarte terre, List<string> lieux, List<string> registres)> MontrerAvecRegistre(DocumentDuMonde registre, bool refuse = false)
        {
            var bulle = racine.GetComponent<InfobulleDeTerre>(); bulle.automatique = true; var terre = Terre(20, "Bourg témoin"); var lieux = new List<string>(); var registres = new List<string>();
            bulle.Lecture = new LectureDossier(c => { lieux.Add(c); return System.Threading.Tasks.Task.FromResult(DocTerre(20, "Bourg témoin")); });
            bulle.LectureModificateurs = new LectureDossier(c => { registres.Add(c); return refuse ? System.Threading.Tasks.Task.FromException<DocumentDuMonde>(new ArgumentException("refus témoin")) : System.Threading.Tasks.Task.FromResult(registre); });
            bulle.Pas(O, terre, 0); await Fin(bulle.Lecture); await Fin(bulle.LectureModificateurs); bulle.Pas(O, terre, 0.5); return (bulle, terre, lieux, registres);
        }
        [Test] public async System.Threading.Tasks.Task LInfobulleDUneTerreSansPoseResteCelleDAvant()
        {
            string avant = InfobulleDeTerre.Decrire(null, DocTerre(20, "Bourg témoin"), null, 20, 0);
            var (bulle, _, _, registres) = await MontrerAvecRegistre(DocModificateurs(8, Lieu(30, 0, Grandeur("departs", "Départs", 0.1, POSE_MOULIN)), Lieu(20, 1, Grandeur("commerce", "Commerce", 0.1, POSE_MOULIN))));
            Assert.That(registres, Is.Not.Empty); Assert.That(bulle.TexteAffiche, Is.EqualTo(avant)); Assert.That(bulle.TexteAffiche.Split('\n'), Has.Length.EqualTo(avant.Split('\n').Length));
            (bulle, _, _, _) = await MontrerAvecRegistre(DocModificateurs(8)); Assert.That(bulle.TexteAffiche, Is.EqualTo(avant));
        }
        [Test] public async System.Threading.Tasks.Task LInfobulleDUneTerreDitLesPosesDeSonBourgPuisLeTotalDeChaqueGrandeur()
        {
            var (bulle, terre, lieux, registres) = await MontrerAvecRegistre(TroisPoses());
            string trois = InfobulleDeTerre.Decrire(null, DocTerre(20, "Bourg témoin"), null, 20, 0);
            Assert.That(bulle.TexteAffiche, Is.EqualTo(trois + "\n" + string.Join("\n", LIGNES_ATTENDUES)));
            Assert.That(InfobulleDeTerre.DecrireModificateurs(TroisPoses(), 20), Is.EqualTo(LIGNES_ATTENDUES)); Assert.That(InfobulleDeTerre.DecrireModificateurs(TroisPoses(), 7), Is.Empty);
            Assert.That(lieux, Is.EqualTo(new[] { "/lieu?cell=20" })); Assert.That(registres, Is.EqualTo(new[] { "/modificateurs" }));
            Assert.That(TexteDuMonde.Interdit(bulle.TexteAffiche, "batiment:moulin-paris", "idee:assolement", "evenement:epreuve-de-l-infobulle", "m-1", "grande-3"), Is.Null, bulle.TexteAffiche);
            Canvas.ForceUpdateCanvases(); var feuillet = racine.transform.Find("Cabinet").GetComponentsInChildren<RectTransform>().Single(r => r.name == "Infobulle"); Assert.That(feuillet.GetComponentInChildren<Text>().text, Is.EqualTo(bulle.TexteAffiche));
            // Les relectures n'allongent que le même chemin, à la même période que /lieu.
            bulle.Pas(O, terre, 1); Assert.That(registres, Has.Count.EqualTo(1)); bulle.Pas(O, terre, 2.5); Assert.That(registres, Is.EqualTo(new[] { "/modificateurs", "/modificateurs" })); Assert.That(lieux, Is.EqualTo(new[] { "/lieu?cell=20", "/lieu?cell=20" }));
        }
        [Test] public async System.Threading.Tasks.Task LInfobulleNeMontreRienDePlusSiLesModificateursSontAUnAutreTickOuEnEchec()
        {
            string avant = InfobulleDeTerre.Decrire(null, DocTerre(20, "Bourg témoin"), null, 20, 0);
            var (bulle, _, _, _) = await MontrerAvecRegistre(TroisPoses(9)); Assert.That(bulle.TexteAffiche, Is.EqualTo(avant));
            (bulle, _, _, _) = await MontrerAvecRegistre(TroisPoses(7)); Assert.That(bulle.TexteAffiche, Is.EqualTo(avant));
            var refusee = await MontrerAvecRegistre(null, true); bulle = refusee.bulle; Assert.That(refusee.registres, Is.Not.Empty); Assert.That(bulle.LectureModificateurs.Erreur, Is.EqualTo("refus témoin")); Assert.That(bulle.TexteAffiche, Is.EqualTo(avant));
            // Contre-épreuve : au même tick, les lignes viennent.
            (bulle, _, _, _) = await MontrerAvecRegistre(TroisPoses(8)); Assert.That(bulle.TexteAffiche, Is.Not.EqualTo(avant).And.StartWith(avant));
        }
        [Test] public void UneDureeEnJoursSAccordeEtLaFinAbsenteDitLaSource()
        {
            string un = POSE_EPREUVE.Replace("90", "1"); var lignes = InfobulleDeTerre.DecrireModificateurs(DocModificateurs(8, Lieu(20, 0, Grandeur("natalite", "Natalité", -0.05, un, POSE_MOULIN))), 20);
            Assert.That(lignes[0], Does.EndWith(" · encore 1 jour")); Assert.That(lignes[1], Does.EndWith(" · tant que sa source tient"));
            Assert.Throws<ArgumentException>(() => InfobulleDeTerre.DecrireModificateurs(DocModificateurs(8, Lieu(20, 0, Grandeur("natalite", "Natalité", -0.05, POSE_EPREUVE.Replace(",\"source_dite\":\"événement\"", ""))) ), 20));
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
        // La bande des modes et sa légende, posées sur la carte en bas de l'écran, ne passent sous aucun panneau.
        static Rect Zone(RectTransform t, float k) // en unités d'écran, origine en haut à gauche, pour une toile de 1920 × k de large
        {
            Assert.That(t.anchorMin, Is.EqualTo(t.anchorMax), t.name + " : ancres étirées"); float x = t.anchorMin.x * 1920 + t.anchoredPosition.x - t.pivot.x * t.sizeDelta.x;
            return new Rect(x * k, ((1 - t.anchorMin.y) * 1080 - t.anchoredPosition.y - (1 - t.pivot.y) * t.sizeDelta.y) * k, t.sizeDelta.x * k, t.sizeDelta.y * k);
        }
        static string Recouvert(Transform toile, Rect zone, float k) => toile.Cast<Transform>().Where(e => e.GetComponent<Image>() is Image i && i.raycastTarget
            && !new[] { "Infobulle", CalquesCarte.BANDE, CalquesCarte.LEGENDE }.Contains(e.name)).FirstOrDefault(e => zone.Overlaps(Zone((RectTransform)e, k)))?.name;
        [Test] public void La_bande_des_modes_et_sa_legende_restent_a_leur_place()
        {
            Transform toile = racine.transform.Find("Cabinet"); var bande = (RectTransform)toile.Find(CalquesCarte.BANDE); var fond = (RectTransform)toile.Find(CalquesCarte.LEGENDE);
            var cinq = (ModeDeCarte[])Enum.GetValues(typeof(ModeDeCarte)); string[] noms = cinq.Select(m => m.ToString()).ToArray();
            foreach (var mode in cinq)
            {
                var bouton = bande.Find(mode.ToString())?.GetComponent<Button>(); Assert.That(bouton, Is.Not.Null, mode.ToString()); string phrase = bouton.GetComponent<Infobulle>()?.Phrase;
                Assert.That(phrase, Is.EqualTo(CalquesCarte.PhraseDuMode(mode)).And.StartWith(mode + " : ").And.Not.EqualTo(mode.ToString()), mode + " : phrase « " + phrase + " »");
                // Réduit à son icône : 56 × 44, aucun texte montré, l'image de la planche ou, faute d'elle, le signe gravé.
                string motif = EmblemeCommande.Motif(mode.ToString()); Transform icone = bouton.transform.Find(CalquesCarte.ICONE + motif), signe = bouton.transform.Find("Repère " + motif);
                Assert.That(((RectTransform)bouton.transform).sizeDelta, Is.EqualTo(new Vector2(CalquesCarte.LARGEUR_D_UN_MODE, SocleInterface.HauteurCommande)), mode.ToString());
                Assert.That(bouton.GetComponentsInChildren<Text>(false), Is.Empty, mode + " écrit encore son nom");
                Assert.That(icone != null && icone.gameObject.activeSelf || signe != null && signe.gameObject.activeSelf, Is.True, mode + " sans icône");
                bool livree = Resources.Load<Texture2D>(CalquesCarte.Planche(mode)) != null;
                Assert.That(livree ? icone != null && icone.gameObject.activeSelf && !signe.gameObject.activeSelf : icone == null, Is.True, mode + " : la planche " + (livree ? "livrée n'est pas montrée" : "absente est montrée"));
            }
            Assert.That(Zone(bande, 1).center.x, Is.EqualTo(Zone(fond, 1).center.x).Within(.5f), "la bande n'est pas centrée sous la légende");
            Assert.That(toile.Find("Parcourir le monde"), Is.Null, "le panneau « Parcourir le monde » est encore posé");
            Button[] modes = toile.GetComponentsInChildren<Button>(true).Where(b => noms.Contains(b.name) && b.transform.parent == bande).ToArray();
            Assert.That(modes.Length == 5 && modes.Select(b => b.name).Distinct().Count() == 5 && bande.childCount == 5, Is.True, string.Join(", ", modes.Select(b => b.transform.parent.name + "/" + b.name)));
            Assert.That(bande.Cast<Transform>().All(b => b.name != "Puissances" && b.name != "Habitants" && b.name != "Flux"), Is.True, "un bouton d'hier reste dans la bande");
            var calques = racine.GetComponent<CalquesCarte>();
            var servis = new LieuxLus(364, new DateDuMonde(1400, 365), 2, new[] { new CelluleServie(10, new[] { new LieuServi(0, 1, 7400, 0) }), new CelluleServie(20, new[] { new LieuServi(0, 275000, 900, 12345), new LieuServi(1, 3, 28000, -40) }) });
            var terres = new TerresDeLaCarte(364, new DateDuMonde(1400, 365), new[] { new PaysDeLaCarte("pays-a", "Avalon") }, new[] { new TerreLue(10, "m10", "pays-a") });
            var guerres = new GuerresLues(364, new DateDuMonde(1400, 365), new[] { new GuerreLue(1, "m10", "m20", 3) }, new[] { new ArmeeLue(0, "m10", 10, 0, 1200, 500, 10, null, new long[0], new PointCarte(0, 0), new PointCarte[0]) }, new PriseLue[0], 0);
            var carteLue = new CarteLue(2, new[] { new CelluleDeCarte(10, new PolygoneDeCarte[0], null, null, new VilleDeCarte[0], "marais", 7400), new CelluleDeCarte(20, new PolygoneDeCarte[0], null, null, new VilleDeCarte[0], null, 28900) });
            foreach (var mode in cinq)
            {
                var lecture = new LectureDuMode(mode, servis, carteLue, terres, guerres); string texte = lecture.Legende;
                string detail = lecture.Detail; Assert.That(lecture.Echelle, Is.Not.Null, mode + " sans échelle"); calques.Legender(lecture.Echelle, detail);
                foreach (var etiquette in calques.EtiquettesDeLEchelle) foreach (float echelle in new[] { 1f, 2f / 3f }) Assert.That(CalquesCarte.Lignes(etiquette, etiquette.text, echelle), Is.EqualTo(1), mode + " : « " + etiquette.text + " » à l'échelle " + echelle);
                Assert.That(calques.Legende.text == texte && fond.GetComponent<Infobulle>().Phrase == texte + "\n" + detail && calques.Echelle.transform.parent == fond && calques.Echelle.gameObject.activeSelf, Is.True, mode.ToString());
                Assert.That(Zone(fond, 1).yMax, Is.EqualTo(1004f).Within(.01f), mode + " : le bas de la légende");
                foreach (var (largeur, hauteur) in new[] { (1920f, 1080f), (1280f, 720f) }) foreach (var zone in new[] { bande, fond })
                {
                    Rect r = Zone(zone, largeur / 1920); string sous = Recouvert(toile, r, largeur / 1920); Assert.That(sous, Is.Null, zone.name + " recouvre « " + sous + " » en " + largeur + " × " + hauteur + " (" + mode + ")");
                    Assert.That(r.xMin >= 0 && r.yMin >= 0 && r.xMax <= largeur && r.yMax <= hauteur, Is.True, zone.name + " " + r + " hors de l'écran en " + largeur + " × " + hauteur);
                }
            }
            Assert.That(fond.GetComponent<Image>().raycastTarget && bande.parent == toile && fond.parent == toile, Is.True);
            Assert.That(new Rect(24, 872, 1238, 184).Overlaps(Zone(bande, 1)), Is.True, "contre-épreuve : un guide de 1238 de large recouvre la bande");
            Assert.That(Recouvert(toile, new Rect(16, 104, 1100, 160), 1), Is.Not.Null, "contre-épreuve : l'ancienne légende des lieux recouvre un feuillet");
            var etat = racine.GetComponentsInChildren<Text>(true).Single(t => t.name == CabinetDeCarte.ETAT); Assert.That(etat.text, Is.EqualTo("La carte se prépare…")); Assert.That(etat.preferredWidth, Is.LessThanOrEqualTo(600f));
            foreach (var (largeur, hauteur) in new[] { (1920f, 1080f), (1280f, 720f) }) { float k = largeur / 1920; Rect r = Zone(etat.rectTransform, k);
                Assert.That(r.xMin >= 0 && r.yMin >= 0 && r.xMax <= largeur && r.yMax <= hauteur && !r.Overlaps(Zone(bande, k)) && !r.Overlaps(Zone(fond, k)), Is.True, "l'état " + r + " hors de l'écran, ou sur la bande, en " + largeur + " × " + hauteur); }
        }
        // Le mode en cours est enfoncé, et lui seul ; le choisir ne bouge ni la vue, ni la caméra, ni la terre gardée.
        [Test] public void Le_mode_en_cours_est_enfonce_et_en_changer_ne_bouge_ni_la_vue_ni_la_terre_gardee()
        {
            Preparer(); Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); var sept = Terre(7, "Ville test"); cabinet.Garder(sept); cabinet.Afficher();
            var calques = racine.GetComponent<CalquesCarte>(); var cinq = (ModeDeCarte[])Enum.GetValues(typeof(ModeDeCarte));
            ModeDeCarte[] Enfonces() => cinq.Where(calques.Enfonce).ToArray();
            Assert.That(Enfonces(), Is.EqualTo(new[] { ModeDeCarte.Politique }), "le cabinet ne s'ouvre pas sur la carte politique enfoncée");
            Vector2 centre = carte.Vue.Centre; float demi = carte.Vue.Demi; Vector3 place = camera.transform.position;
            foreach (var mode in new[] { ModeDeCarte.Relief, ModeDeCarte.Guerres, ModeDeCarte.Vivres, ModeDeCarte.Population, ModeDeCarte.Politique, ModeDeCarte.Vivres })
            {
                var bouton = calques.BoutonDu(mode); bouton.onClick.Invoke(); Peindre(calques); cabinet.Afficher();
                Assert.That(calques.Mode, Is.EqualTo(mode)); Assert.That(Enfonces(), Is.EqualTo(new[] { mode }), "un seul bouton enfoncé, celui du mode cliqué");
                var filets = bouton.transform.Find(CalquesCarte.TRAIT)?.GetComponentsInChildren<Image>(false) ?? new Image[0];
                Assert.That(filets.Length == 4 && filets.All(f => f.color == SocleInterface.Couleur("or-vieilli") && !f.raycastTarget && Mathf.Min(f.rectTransform.rect.width, f.rectTransform.rect.height) == CalquesCarte.TRAIT_ENFONCE), Is.True, mode + " : sans cadre d'or vieilli de quatre pixels");
                foreach (var autre in cinq.Where(m => m != mode)) Assert.That(calques.BoutonDu(autre).transform.Find(CalquesCarte.TRAIT).gameObject.activeSelf, Is.False, autre + " garde son cadre");
                Assert.That(bouton.colors.normalColor, Is.EqualTo(SocleInterface.Couleur("fond")), mode + " : sa matière n'est pas pressée");
                foreach (var autre in cinq.Where(m => m != mode)) Assert.That(calques.BoutonDu(autre).colors.normalColor, Is.EqualTo(SocleInterface.Couleur("secondaire")), autre + " reste pressé");
                Assert.That((carte.Vue.Centre, carte.Vue.Demi, camera.transform.position, cabinet.Retenue), Is.EqualTo((centre, demi, place, sept)), mode + " a bougé la vue ou lâché la terre gardée");
            }
            // Contre-épreuve : un geste de la vue la change bien, et la caméra la suit.
            carte.Vue.Centrer(centre + new Vector2(40, -30), demi / 2); cabinet.Afficher();
            Assert.That(carte.Vue.Centre == centre || carte.Vue.Demi == demi, Is.False, "échantillon vide : la vue ne bouge pas");
        }
        [Test] public void Changer_de_mode_ne_touche_ni_l_horloge_ni_les_lectures()
        {
            // La lecture du monde attend la porte : la contre-épreuve voit la partie occupée, quel que soit le fil qui reprend la tâche.
            using var porte = new System.Threading.ManualResetEventSlim(false);
            int appels = 0; partie = new LecturePartie(() => { appels++; porte.Wait(5000); return Lecture<MondeAvecMaisonLu>.Absent("lecture témoin"); }, _ => { appels++; return null; }, () => { appels++; return null; }, _ => { appels++; return null; }); cabinet.Partie = partie;
            var monde = Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(1, new DateDuMonde(1400, 1), 0, new CelluleDuMonde[0]), null)); Poser(partie, "Monde", monde);
            var horlogeDeCarte = racine.GetComponent<HorlogeDeCarte>(); var lue = new HorlogeLue(7, new DateDuMonde(1400, 8), 2); Poser(horlogeDeCarte, "Lue", lue);
            var calques = racine.GetComponent<CalquesCarte>(); Transform bande = racine.transform.Find("Cabinet/" + CalquesCarte.BANDE);
            foreach (var mode in new[] { ModeDeCarte.Vivres, ModeDeCarte.Population, ModeDeCarte.Relief, ModeDeCarte.Guerres, ModeDeCarte.Politique }) { bande.Find(mode.ToString()).GetComponent<Button>().onClick.Invoke(); Assert.That(calques.Mode, Is.EqualTo(mode)); }
            Assert.That(appels == 0 && !partie.Occupee && ReferenceEquals(partie.Monde, monde) && !horlogeDeCarte.RequeteEnVol && ReferenceEquals(horlogeDeCarte.Lue, lue), Is.True, appels + " lecture(s), occupée " + partie.Occupee);
            _ = partie.Actualiser(); Assert.That(partie.Occupee, Is.True, "contre-épreuve : une lecture lancée occupe la partie"); porte.Set();
        }
        // La barre du haut dit la maison, sa part et son grenier, lus aux comptes servis au tick du monde lu.
        const string BARRE = "Lecture de la maison…", ATTENTE = "Comptes en attente du monde", LIGNE_DE_LA_BARRE = "Maison témoin · Prélèvement : 25 % · Grenier : bois : 0 kg · nourriture : 1,23 t";
        static Lecture<ComptesDeMaison> ComptesBarre(string id, long? tick, double? part = 0.25, Dictionary<string, double> grenier = null) => Lecture<ComptesDeMaison>.De(new ComptesDeMaison(
            new MaisonLue(id, "Maison témoin", new SiegeDeMaison(10, 0, "Siège", new PointCarte(1, 2)), new[] { new LieuTenu(10, 0) }, new Dictionary<string, string>()),
            null, part, grenier ?? new Dictionary<string, double> { ["nourriture"] = 1234.5, ["bois"] = 0 }, new FluxDeMaison(0, 0, 0, 0, 0, 0, 0, null), tick));
        string LaBarre(Lecture<ComptesDeMaison> comptes) { Poser(partie, "Comptes", comptes); cabinet.Afficher(); string t = Propre(BARRE); Assert.That(TexteDuMonde.Interdit(t, JOUEUR, B), Is.Null, t); return t; }
        [Test] public void La_barre_egale_les_comptes_servis_au_meme_tick()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); Assert.That(LaBarre(ComptesBarre(JOUEUR, 1)), Is.EqualTo(LIGNE_DE_LA_BARRE));
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
            Assert.That(LaBarre(ComptesBarre(JOUEUR, 1)), Is.EqualTo(LIGNE_DE_LA_BARRE), "remis au tick du monde");
            Assert.That(LaBarre(Lecture<ComptesDeMaison>.Absent("refus témoin")), Is.EqualTo("Comptes indisponibles : refus témoin"));
        }
        [Test] public void Sans_maison_la_barre_le_dit()
        {
            Proposer(); Assert.That(Propre(BARRE), Is.EqualTo("Aucune maison choisie"));
            Poser(partie, "Comptes", ComptesBarre(JOUEUR, 1)); cabinet.Afficher(); Assert.That(Propre(BARRE), Is.EqualTo("Aucune maison choisie"), "des comptes sans maison du joueur ne s'affichent pas");
            Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.Absent("service coupé")); cabinet.Afficher(); Assert.That(Propre(BARRE), Is.EqualTo("Maison indisponible : service coupé"));
            Poser(partie, "Monde", null); cabinet.Afficher(); Assert.That(Propre(BARRE), Is.EqualTo(BARRE));
            Assert.That(racine.GetComponentsInChildren<Button>().Count(b => b.transform.parent.name == "FORGE · Le cabinet" && b.name != BoutonDeLaVille.NOM), Is.EqualTo(3), "la barre n'est pas une commande");
        }
        // Le choix reçu, la maison pas encore servie : la barre nomme le pays choisi. La maison servie : chaque ligne s'ouvre sur le pays du joueur, quand on le connaît.
        [Test] public void La_barre_nomme_le_pays_choisi_puis_le_pays_du_joueur()
        {
            var sans = MondeDe(null); var avec = MondeDe(JOUEUR); var recu = RecuIntention.AccepteeAu(7);
            Assert.That(CabinetDeCarte.Barre(sans, null, recu, "France"), Is.EqualTo("France · choix reçu, le monde l'applique à son premier jour"));
            Assert.That(CabinetDeCarte.Barre(sans, null, recu), Is.EqualTo("Choix reçu, le monde l'applique à son premier jour"));
            Assert.That(CabinetDeCarte.Barre(sans, null, RecuIntention.Refusee(409, "refus"), "France"), Is.EqualTo("Aucune maison choisie"), "un refus n'est pas un choix");
            Assert.That(CabinetDeCarte.Barre(sans, null, null, "France"), Is.EqualTo("Aucune maison choisie"), "rien n'est parti");
            Assert.That(CabinetDeCarte.Barre(sans, ComptesBarre(JOUEUR, 1)), Is.EqualTo("Aucune maison choisie"));
            var comptes = ComptesBarre(JOUEUR, 1);
            Assert.That(CabinetDeCarte.Barre(avec, comptes, recu, "Bohême", "France"), Is.EqualTo("France · " + LIGNE_DE_LA_BARRE), "la maison servie passe devant le choix reçu");
            Assert.That(CabinetDeCarte.Barre(avec, comptes), Is.EqualTo(LIGNE_DE_LA_BARRE), "sans pays du joueur, la ligne ne change pas");
            Assert.That(CabinetDeCarte.Barre(avec, null, null, null, "France"), Is.EqualTo("France · " + ATTENTE));
            Assert.That(CabinetDeCarte.Barre(avec, null), Is.EqualTo(ATTENTE));
            var absent = Lecture<ComptesDeMaison>.Absent("refus témoin");
            Assert.That(CabinetDeCarte.Barre(avec, absent, null, null, "France"), Is.EqualTo("France · Comptes indisponibles : refus témoin"));
            Assert.That(CabinetDeCarte.Barre(avec, absent), Is.EqualTo("Comptes indisponibles : refus témoin"));
        }
        // « Terres et comptes » et « Autres maisons » sont deux icônes de la barre du haut, chacune avec son motif et sa phrase ; leurs feuillets ne recouvrent jamais la barre.
        static Rect Monde(RectTransform t) { var c = new Vector3[4]; t.GetWorldCorners(c); return Rect.MinMaxRect(c.Min(v => v.x), c.Min(v => v.y), c.Max(v => v.x), c.Max(v => v.y)); }
        [Test] public void Chaque_icone_de_la_barre_a_sa_phrase_et_son_motif()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); // l'accueil fermé : « Votre maison » peut s'ouvrir
            Transform toile = racine.transform.Find("Cabinet"), conteneur = toile.Find("FORGE · Le cabinet/" + CabinetDeCarte.DOSSIERS); Assert.That(conteneur, Is.Not.Null, "dossiers de la barre introuvables");
            Button[] icones = conteneur.GetComponentsInChildren<Button>(true).OrderBy(b => ((RectTransform)b.transform).anchoredPosition.x).ToArray();
            Assert.That(icones.Select(b => b.name), Is.EqualTo(new[] { "Votre maison", "Terres et comptes", "Autres maisons" }));
            Assert.That(icones.Select(b => ((RectTransform)b.transform).anchoredPosition.x), Is.EqualTo(new[] { 0f, CabinetDeCarte.PAS_DES_ICONES, 2 * CabinetDeCarte.PAS_DES_ICONES }), "les icônes ne sont pas au pas de la barre");
            Assert.That(((RectTransform)conteneur).sizeDelta.x, Is.EqualTo(2 * CabinetDeCarte.PAS_DES_ICONES + 56), "les dossiers ne tiennent pas leurs trois icônes");
            string[] titres = { "Votre maison", "Terres et comptes", "Les autres maisons" }, motifs = { "ecu", "coffre", "maisons" };
            for (int i = 0; i < 3; i++)
            {
                Button icone = icones[i]; string phrase = icone.GetComponent<Infobulle>()?.Phrase;
                Assert.That(((RectTransform)icone.transform).sizeDelta, Is.EqualTo(new Vector2(56, 44)), icone.name);
                Assert.That(icone.GetComponentsInChildren<Text>().Select(t => t.text), Is.Empty, icone.name + " écrit encore son nom");
                Assert.That(icone.transform.Find("Repère " + motifs[i]) != null && icone.transform.Find("Repère livre") == null, Is.True, icone.name + " : motif absent, ou livre du Menu");
                Assert.That(!string.IsNullOrWhiteSpace(phrase) && phrase != icone.name && icones.Where(b => b != icone).All(b => b.GetComponent<Infobulle>()?.Phrase != phrase) && phrase.StartsWith(titres[i] + " : ", StringComparison.Ordinal), Is.True, icone.name + " : « " + phrase + " »");
                var feuillet = toile.Cast<Transform>().Single(t => t.name == titres[i] && t.Find("Filet") != null).gameObject;
                Assert.That(feuillet.activeSelf, Is.False, titres[i] + " ouvert d'avance"); icone.onClick.Invoke(); Assert.That(feuillet.activeSelf, Is.True, titres[i] + " reste fermé au clic");
                icone.onClick.Invoke(); Assert.That(feuillet.activeSelf, Is.False, titres[i] + " reste ouvert au second clic");
            }
            foreach (var nom in new[] { "Votre maison", "Terres et comptes", "Autres maisons" }) { Assert.That(toile.GetComponentsInChildren<Button>(true).Count(b => b.name == nom), Is.EqualTo(1), nom + " : un seul bouton dans la toile");
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
            // La date raccourcie laisse sa place à « Entrer dans la ville », de x 888 à 1104, avant les dossiers.
            Text date = Nomme("Lecture de la date…"); Assert.That(date.rectTransform.sizeDelta.x, Is.EqualTo(400f));
            // La ligne la plus longue de l'horloge (le dernier jour, le dernier palier) tient aussi, sur sa seule ligne.
            var lignes = new[] { "Date indisponible : le monde ne répond pas" }.Concat(new[] { 0.5, 1.5, 20 }.Select(v => HorlogeDeCarte.Decrire(new HorlogeLue(364, new DateDuMonde(1400, 365), v))));
            foreach (string texte in lignes) { date.text = texte; TestContext.WriteLine("largeur de la date « " + texte + " » : " + date.preferredWidth + " sur 400"); Assert.That(date.preferredWidth, Is.LessThanOrEqualTo(400f), texte); }
            Assert.That(icones.Overlaps(Monde((RectTransform)Commande(BoutonDeLaVille.NOM).transform)), Is.False, "les icônes recouvrent « Entrer dans la ville »");
        }
        // Le panneau « Parcourir le monde » quitte le bas de la carte ; ses commandes restent à leur place, son aide passe au Menu, l'état de la carte au centre de sa vue.
        [Test] public void Aucun_panneau_Parcourir_le_monde_ne_reste()
        {
            const string NOM = "Parcourir le monde"; Transform toile = racine.transform.Find("Cabinet");
            Transform[] Restes() => racine.GetComponentsInChildren<Transform>(true).Where(t => t.name == NOM || t.TryGetComponent<Text>(out var texte) && texte.text.Contains(NOM)).ToArray();
            Assert.That(Restes().Select(t => t.name), Is.Empty);
            Assert.That(System.IO.File.ReadAllText("Assets/Interface/CabinetDeCarte.cs"), Does.Not.Contain(NOM));
            Button[] boutons = toile.GetComponentsInChildren<Button>(true);
            Button Seul(string nom) { Button[] trouves = boutons.Where(b => b.name == nom).ToArray(); Assert.That(trouves, Has.Length.EqualTo(1), nom + " : un seul bouton dans la toile"); return trouves[0]; }
            Transform bande = toile.Find(CalquesCarte.BANDE), conteneur = toile.Find("FORGE · Le cabinet/" + CabinetDeCarte.DOSSIERS);
            foreach (var nom in Enum.GetNames(typeof(ModeDeCarte))) Assert.That(Seul(nom).transform.parent, Is.SameAs(bande), nom + " hors de la bande des modes");
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
            Rect r = Zone(etat.rectTransform, 1); Assert.That(Vector2.Distance(r.center, new Vector2(1920 / 2, 540)), Is.LessThanOrEqualTo(1f), "l'état " + r + " hors du centre de l'écran"); Assert.That(etat.raycastTarget, Is.False); Assert.That(etat.alignment, Is.EqualTo(TextAnchor.MiddleCenter));
            Poser(dessinee, "CellulesServies", 12); cabinet.Afficher(); Assert.That(etat.gameObject.activeSelf, Is.False, "carte servie : l'état reste affiché");
            Poser(dessinee, "CellulesServies", -1); cabinet.Afficher(); Assert.That(etat.gameObject.activeSelf, Is.True, "remise à −1 : l'état ne revient pas");
        }
        // La barre des jauges, sous la barre des comptes, lit le pays servi au tick du monde lu.
        const string EN_ATTENTE = "Jauges en attente du monde";
        static readonly string[] NOMS_JAUGES = { "Concorde", "Renom", "Droit", "Plume", "Sceau", "Épée" };
        static Lecture<PaysLu> PaysTemoin(string id, long tick, double concorde = 0, double renom = 12.34, double droit = 50, double plume = 5, double sceau = 0, double epee = 3.5, bool chef = true, long diplomatie = 0, params PoseLue[] poses)
        {
            var comp = chef ? new Dictionary<string, long> { ["gestion"] = 10, ["diplomatie"] = diplomatie, ["guerre"] = 7 } : null;
            JaugeLue J(string nom, string dit, double v, double min, double max, double neutre) => new JaugeLue(nom, dit, v, min, max, neutre);
            PointsLus P(string nom, string dit, double v, string domaine) => new PointsLus(nom, dit, v, 999, domaine, comp == null ? (double?)null : comp[domaine] * 0.5);
            return Lecture<PaysLu>.De(new PaysLu(id, "Maison témoin", tick, new DateDuMonde(1400, tick + 1),
                new Dictionary<string, JaugeLue> { ["concorde"] = J("Concorde", "si le pays tient ensemble : la stabilité", concorde, -3, 3, 0), ["renom"] = J("Renom", "ce qu'on dit du pays et de sa dynastie : le prestige", renom, 0, 100, 0),
                    ["droit"] = J("Droit", "ce qui fonde le souverain : la légitimité", droit, 0, 100, 50) },
                new Dictionary<string, PointsLus> { ["plume"] = P("Plume", "administrer", plume, "gestion"), ["sceau"] = P("Sceau", "traiter", sceau, "diplomatie"), ["epee"] = P("Épée", "combattre", epee, "guerre") },
                comp, chef ? null : "chef de la maison non connu : aucun point", poses));
        }
        static PoseLue Pose(string jauge, string grandeur, string nom, double valeur) => new PoseLue(grandeur, nom, valeur, jauge);
        Transform Jauges => racine.transform.Find("Cabinet/FORGE · Le cabinet/" + BarreDuPays.NOM);
        Text Cellule(string nom) => Jauges.Find(nom).GetComponent<Text>();
        string Phrase(string nom) => Cellule(nom).GetComponent<Infobulle>().Phrase;
        string[] Cellules() => NOMS_JAUGES.Select(n => Cellule(n).text).ToArray();
        string EtatDesJauges() => Jauges.GetComponentsInChildren<Text>(true).Single(t => !NOMS_JAUGES.Contains(t.name)).text;
        void LesJauges(Lecture<PaysLu> pays, long tick = 1)
        {
            Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(tick, new DateDuMonde(1400, tick + 1), 0, new CelluleDuMonde[0]), JOUEUR)));
            Poser(partie, "Pays", pays); cabinet.Afficher();
        }
        void SansCellule() => Assert.That(Jauges.GetComponentsInChildren<Text>().Any(t => NOMS_JAUGES.Contains(t.name)), Is.False, "une cellule reste active");
        void AucunSens() => Assert.That(Cellules().Any(t => t.Contains("en baisse") || t.Contains("en hausse")), Is.False);

        [Test] public void Les_jauges_de_la_barre_egalent_le_pays_servi_au_meme_tick()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); LesJauges(PaysTemoin(JOUEUR, 1));
            Assert.That(Cellules(), Is.EqualTo(new[] { "Concorde 0 point", "Renom 12,3 points", "Droit 50 points", "Plume 5 points, +5 points/mois", "Sceau 0 point, +0 point/mois", "Épée 3,5 points, +3,5 points/mois" }));
            Assert.That(NOMS_JAUGES.All(n => Cellule(n).isActiveAndEnabled), Is.True); Assert.That(Jauges.GetComponentsInChildren<Text>().Count(t => !NOMS_JAUGES.Contains(t.name)), Is.Zero, "l'état reste actif");
            foreach (var (pays, tick, etape) in new[] { (PaysTemoin(JOUEUR, 0), 1L, "tick 0"), (PaysTemoin(JOUEUR, 2), 1L, "tick 2"), (PaysTemoin(B, 1), 1L, "autre maison"), ((Lecture<PaysLu>)null, 1L, "sans pays") })
            {
                LesJauges(pays, tick); Assert.That(EtatDesJauges(), Is.EqualTo(EN_ATTENTE), etape); SansCellule();
                Assert.That(racine.transform.Find("Cabinet/FORGE · Le cabinet").GetComponentsInChildren<Text>(true).Any(t => t.text.Contains("12,3")), Is.False, etape);
            }
            LesJauges(PaysTemoin(JOUEUR, 1)); Assert.That(Cellule("Renom").text, Is.EqualTo("Renom 12,3 points"), "remis au tick du monde");
            LesJauges(Lecture<PaysLu>.Absent("refus témoin")); Assert.That(EtatDesJauges(), Is.EqualTo("Jauges indisponibles : refus témoin")); SansCellule();
            Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.Absent("service coupé")); cabinet.Afficher(); Assert.That(EtatDesJauges(), Is.EqualTo("Pays indisponible : service coupé"));
            Poser(partie, "Monde", null); cabinet.Afficher(); Assert.That(EtatDesJauges(), Is.EqualTo("Lecture du pays…"));
            Poser(partie, "Monde", MondeDe(null)); cabinet.Afficher(); Assert.That(Jauges.GetComponentsInChildren<Text>().Any(t => t.gameObject.activeInHierarchy), Is.False);
            Assert.That(racine.GetComponentsInChildren<Button>().Count(b => b.transform.parent.name == "FORGE · Le cabinet" && b.name != BoutonDeLaVille.NOM), Is.EqualTo(3), "la barre n'est pas une commande");
        }
        [Test] public void Une_jauge_que_le_service_ne_sert_pas_est_nommee()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); var p = PaysTemoin(JOUEUR, 1).Donnees; var sans = p.Jauges.Where(e => e.Key != "droit").ToDictionary(e => e.Key, e => e.Value);
            LesJauges(Lecture<PaysLu>.De(new PaysLu(p.MaisonId, p.Nom, p.Tick, p.Date, sans, p.Points.ToDictionary(e => e.Key, e => e.Value), p.Competences.ToDictionary(e => e.Key, e => e.Value), null, p.Poses)));
            Assert.That(EtatDesJauges(), Is.EqualTo("Jauges indisponibles : Droit non servie par le monde")); Assert.That(Jauges.GetComponentsInChildren<Text>().Any(t => t.gameObject.activeInHierarchy && NOMS_JAUGES.Contains(t.name)), Is.False);
        }
        [Test] public void Sans_chef_connu_la_barre_dit_l_absence()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); LesJauges(PaysTemoin(JOUEUR, 1, chef: false));
            Assert.That(Cellules().Skip(3), Is.EqualTo(new[] { "Plume 5 points, chef non connu", "Sceau 0 point, chef non connu", "Épée 3,5 points, chef non connu" }));
            foreach (var n in NOMS_JAUGES.Skip(3)) { Assert.That(Cellule(n).text, Does.Not.Contain("+0").And.Not.Contain("/mois"), n); Assert.That(Phrase(n), Does.Contain("absent, pas nul"), n); Assert.That(TexteDuMonde.Interdit(Phrase(n), JOUEUR, B) ?? TexteDuMonde.SansUnite(Phrase(n)), Is.Null, Phrase(n)); }
            string sans = Cellule("Sceau").text;
            var zero = PaysTemoin(JOUEUR, 1, sceau: 0).Donnees; // les compétences et les gains à 0 : un vrai zéro, mesuré
            LesJauges(Lecture<PaysLu>.De(new PaysLu(JOUEUR, zero.Nom, zero.Tick, zero.Date, zero.Jauges.ToDictionary(e => e.Key, e => e.Value),
                zero.Points.ToDictionary(e => e.Key, e => new PointsLus(e.Value.Nom, e.Value.Dit, 0, e.Value.Plafond, e.Value.Domaine, 0d)), new Dictionary<string, long> { ["gestion"] = 0, ["diplomatie"] = 0, ["guerre"] = 0 }, null, zero.Poses)));
            Assert.That(Cellule("Plume").text, Is.EqualTo("Plume 0 point, +0 point/mois")); Assert.That(Cellule("Sceau").text, Is.Not.EqualTo(sans));
            Assert.That(Phrase("Plume"), Does.Contain("Gagne 0 point par mois : la gestion du chef, 0 point.").And.Not.Contain("absent, pas nul"));
        }
        [Test] public void Une_jauge_qui_baisse_se_voit()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); var departs = Pose("concorde", "departs", "Départs", 0.05); var droit = Pose("droit", "prelevement", "Prélèvement", 0.02);
            LesJauges(PaysTemoin(JOUEUR, 1, 0, 12.34, 50, 5, 31.5, 3.5), 1); AucunSens();
            LesJauges(PaysTemoin(JOUEUR, 2, -1, 12.34, 60, 5, 1.5, 3.5, true, 9, departs, droit), 2);
            Assert.That(Cellules(), Is.EqualTo(new[] { "Concorde -1 point, en baisse", "Renom 12,3 points", "Droit 60 points, en hausse", "Plume 5 points, +5 points/mois", "Sceau 1,5 point, +4,5 points/mois, en baisse", "Épée 3,5 points, +3,5 points/mois" }));
            Assert.That(Phrase("Concorde"), Does.Contain("En baisse depuis le jour 3 de 1400 : de 0 point à -1 point.").And.Contain("Pose au pays : Départs +5 %."));
            Assert.That(Phrase("Droit"), Does.Contain("En hausse depuis le jour 3 de 1400 : de 50 points à 60 points.").And.Contain("Pose au pays : Prélèvement +2 %.").And.EndWith("Relevé au jour 3 de 1400."));
            foreach (var n in NOMS_JAUGES) Assert.That(TexteDuMonde.Interdit(Phrase(n), JOUEUR, B) ?? TexteDuMonde.SansUnite(Phrase(n)), Is.Null, Phrase(n));
            LesJauges(PaysTemoin(JOUEUR, 3, -1, 12.34, 60, 5, 1.5, 3.5, true, 9, departs, droit), 3);
            Assert.That(Cellule("Concorde").text, Is.EqualTo("Concorde -1 point, en baisse")); Assert.That(Cellule("Droit").text, Is.EqualTo("Droit 60 points, en hausse")); Assert.That(Phrase("Concorde"), Does.Contain("depuis le jour 3 de 1400").And.EndWith("Relevé au jour 4 de 1400."));
            LesJauges(PaysTemoin(B, 3), 3); LesJauges(PaysTemoin(JOUEUR, 3, -1, 12.34, 60, 5, 1.5, 3.5, true, 9, departs, droit), 3); AucunSens();
            LesJauges(PaysTemoin(JOUEUR, 1, 0), 1); AucunSens();
        }
        [Test] public void Un_tick_plus_petit_efface_le_sens()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); LesJauges(PaysTemoin(JOUEUR, 1, 0), 1); LesJauges(PaysTemoin(JOUEUR, 2, -1), 2); Assert.That(Cellule("Concorde").text, Does.EndWith(", en baisse"));
            LesJauges(PaysTemoin(JOUEUR, 3, 0), 3); Assert.That(Cellule("Concorde").text, Is.EqualTo("Concorde 0 point, en hausse")); LesJauges(PaysTemoin(JOUEUR, 1, 0), 1); AucunSens();
        }
        [Test] public void Chaque_jauge_dit_d_ou_vient_sa_valeur()
        {
            Publier(JOUEUR, new LieuTenu(10, 0)); LesJauges(PaysTemoin(JOUEUR, 1));
            string[] dits = { "si le pays tient ensemble : la stabilité", "ce qu'on dit du pays et de sa dynastie : le prestige", "ce qui fonde le souverain : la légitimité", "administrer", "traiter", "combattre" };
            for (int i = 0; i < 6; i++)
            {
                string n = NOMS_JAUGES[i], phrase = Phrase(n); Assert.That(Cellule(n).GetComponent<Infobulle>(), Is.Not.Null, n);
                Assert.That(phrase, Does.StartWith(n + " : " + dits[i] + ".").And.EndWith("Relevé au jour 2 de 1400."), n);
                Assert.That(TexteDuMonde.Interdit(phrase, JOUEUR, B) ?? TexteDuMonde.SansUnite(phrase), Is.Null, phrase);
            }
            Assert.That(Phrase("Plume"), Does.Contain("la gestion du chef, 10 points")); Assert.That(Phrase("Concorde"), Does.Contain("À son neutre, elle ne pose rien."));
            Assert.That(Phrase("Droit"), Does.Contain("50 points, de 0 point à 100 points, neutre à 50 points.")); Assert.That(Phrase("Sceau"), Does.Contain("Gagne 0 point par mois : la diplomatie du chef, 0 point."));
            Assert.That(Phrase("Épée"), Does.Contain("3,5 points, au plus 999 points.").And.Contain("Gagne 3,5 points par mois : la guerre du chef, 7 points."));
        }
        [Test] public void Les_jauges_tiennent_dans_le_bandeau()
        {
            var bandeau = (RectTransform)racine.transform.Find("Cabinet/FORGE · Le cabinet"); var conteneur = (RectTransform)bandeau.Find(BarreDuPays.NOM);
            Assert.That(bandeau.sizeDelta, Is.EqualTo(new Vector2(1920, 124))); Assert.That(conteneur.parent, Is.SameAs(bandeau)); Assert.That(conteneur.anchoredPosition, Is.EqualTo(new Vector2(24, -98))); Assert.That(conteneur.sizeDelta, Is.EqualTo(new Vector2(1872, 26)));
            var cadres = NOMS_JAUGES.Select(n => (RectTransform)conteneur.Find(n)).ToArray(); Assert.That(cadres.Select(c => c.anchoredPosition.x), Is.EqualTo(new[] { 0f, 240, 480, 720, 1104, 1488 }));
            for (int i = 0; i < 6; i++)
            {
                Rect r = new Rect(cadres[i].anchoredPosition.x, -cadres[i].anchoredPosition.y, cadres[i].sizeDelta.x, cadres[i].sizeDelta.y);
                Assert.That(r.xMin >= 0 && r.xMax <= 1872 && r.yMax <= 26, Is.True, NOMS_JAUGES[i]); Assert.That(98 + r.yMax, Is.LessThanOrEqualTo(124f), NOMS_JAUGES[i]);
                for (int j = i + 1; j < 6; j++) Assert.That(r.Overlaps(new Rect(cadres[j].anchoredPosition.x, -cadres[j].anchoredPosition.y, cadres[j].sizeDelta.x, cadres[j].sizeDelta.y)), Is.False, NOMS_JAUGES[i] + " / " + NOMS_JAUGES[j]);
            }
            string[] longs = { "Concorde -3 points, en baisse", "Renom 100 points, en baisse", "Droit 100 points, en hausse", "Plume 999 points, +5 points/mois, en baisse", "Sceau 999 points, +5 points/mois, en hausse", "Épée 999 points, +5 points/mois, en baisse" };
            for (int i = 0; i < 6; i++) { var t = Cellule(NOMS_JAUGES[i]); t.text = longs[i]; Assert.That(t.preferredWidth, Is.LessThanOrEqualTo(cadres[i].sizeDelta.x), longs[i]); Assert.That(t.preferredHeight, Is.LessThanOrEqualTo(26f), longs[i]); }
        }

        // Le feuillet « Le pays » lit la partie du cabinet, et son icône est dans le bandeau, hors des dossiers de la barre.
        [Test] public void Le_feuillet_du_cabinet_lit_la_partie()
        {
            Proposer(); Transform toile = racine.transform.Find("Cabinet");
            toile.GetComponentsInChildren<Button>(true).Single(b => b.name == DossierPays.ICONE).onClick.Invoke();
            var dossier = racine.GetComponent<DossierPays>(); Assert.That(dossier, Is.Not.Null); dossier.Pas(0);
            Assert.That(dossier.TexteAffiche, Is.EqualTo("Choisissez une maison pour lire son pays."));
        }
        [Test] public void L_icone_du_pays_ouvre_son_feuillet_hors_des_dossiers()
        {
            Proposer(); Transform toile = racine.transform.Find("Cabinet"); var bandeau = (RectTransform)toile.Find("FORGE · Le cabinet");
            var conteneur = (RectTransform)bandeau.Find(CabinetDeCarte.PAYS); Assert.That(conteneur, Is.Not.Null, "conteneur du pays introuvable dans le bandeau");
            Assert.That(CabinetDeCarte.PAYS, Is.Not.EqualTo(CabinetDeCarte.DOSSIERS)); Assert.That(conteneur.parent, Is.SameAs(bandeau));
            Assert.That(conteneur.anchoredPosition, Is.EqualTo(new Vector2(408, -20))); Assert.That(conteneur.sizeDelta, Is.EqualTo(new Vector2(56, 44)));
            Button[] boutons = conteneur.GetComponentsInChildren<Button>(true); Assert.That(boutons.Select(b => b.name), Is.EqualTo(new[] { "Le pays" }));
            Button icone = boutons[0]; string phrase = icone.GetComponent<Infobulle>()?.Phrase;
            Assert.That(((RectTransform)icone.transform).sizeDelta, Is.EqualTo(new Vector2(56, 44)));
            Assert.That(icone.GetComponentsInChildren<Text>().Select(t => t.text), Is.Empty, "l'icône écrit encore son nom");
            Assert.That(icone.transform.Find("Repère couronne") != null && icone.transform.Find("Repère livre") == null, Is.True, "motif absent, ou livre du Menu");
            Assert.That(!string.IsNullOrWhiteSpace(phrase) && phrase != icone.name && phrase.StartsWith("Le pays : ", StringComparison.Ordinal), Is.True, "« " + phrase + " »");
            Assert.That(toile.GetComponentsInChildren<Button>(true).Count(b => b.name == "Le pays"), Is.EqualTo(1), "un seul bouton « Le pays » dans la toile");
            var feuillet = toile.Cast<Transform>().Single(t => t.name == DossierPays.TITRE && t.GetComponentInChildren<ScrollRect>(true) != null).gameObject;
            Assert.That(feuillet.activeSelf, Is.False, "ouvert d'avance"); icone.onClick.Invoke(); Assert.That(feuillet.activeSelf, Is.True, "fermé au clic");
            Canvas.ForceUpdateCanvases(); Rect cadre = Monde(conteneur), barre = Monde(bandeau), reduite = Rect.MinMaxRect(barre.xMin + .5f, barre.yMin + .5f, barre.xMax - .5f, barre.yMax - .5f);
            Assert.That(Monde((RectTransform)feuillet.transform).Overlaps(reduite), Is.False, "le feuillet ouvert recouvre la barre");
            icone.onClick.Invoke(); Assert.That(feuillet.activeSelf, Is.False, "ouvert au second clic");
            Text titre = bandeau.Find("FORGE · Le cabinet").GetComponent<Text>(); Assert.That(24 + titre.preferredWidth, Is.LessThan(408f), "les glyphes du titre arrivent sous l'icône");
            var menu = (RectTransform)toile.Find("Menu"); Assert.That(menu.anchoredPosition.x + menu.sizeDelta.x, Is.LessThanOrEqualTo(408f), "le Menu recouvre l'icône du pays"); Assert.That(menu.anchoredPosition.x, Is.GreaterThan(24 + titre.preferredWidth), "le Menu recouvre les glyphes du titre");
            foreach (var voisin in new[] { Nomme("Lecture de la date…").rectTransform, Nomme(BARRE).rectTransform, (RectTransform)bandeau.Find(BarreDuPays.NOM), menu })
                Assert.That(cadre.Overlaps(Monde(voisin)), Is.False, "l'icône " + cadre + " recouvre « " + voisin.name + " » " + Monde(voisin));
        }

        // Le panneau des gestes est un enfant du cadre du feuillet « Le pays » ; il s'ouvre et se ferme avec lui, à sa droite, sans toucher un autre panneau.
        static Rect Locale(RectTransform t) // dans son parent, origine en haut à gauche (toutes les ancres sont en haut à gauche)
        {
            Assert.That(t.anchorMin, Is.EqualTo(new Vector2(0, 1)), t.name); Assert.That(t.anchorMax, Is.EqualTo(new Vector2(0, 1)), t.name); Assert.That(t.pivot, Is.EqualTo(new Vector2(0, 1)), t.name);
            return new Rect(t.anchoredPosition.x, -t.anchoredPosition.y, t.sizeDelta.x, t.sizeDelta.y);
        }
        [Test] public void Les_gestes_des_jauges_s_ouvrent_avec_le_feuillet_du_pays()
        {
            Proposer(); Transform toile = racine.transform.Find("Cabinet");
            var gestes = racine.GetComponent<GestesDesJauges>(); Assert.That(gestes, Is.Not.Null, "le cabinet ne porte pas de GestesDesJauges");
            var feuillet = (RectTransform)toile.Cast<Transform>().Single(t => t.name == DossierPays.TITRE && t.GetComponentInChildren<ScrollRect>(true) != null);
            Assert.That(gestes.Panneau.parent, Is.SameAs(feuillet), "le panneau n'est pas dans le cadre du feuillet"); Assert.That(gestes.Panneau.name, Is.EqualTo(GestesDesJauges.TITRE));
            Button icone = toile.GetComponentsInChildren<Button>(true).Single(b => b.name == DossierPays.ICONE);
            Assert.That(gestes.Panneau.gameObject.activeInHierarchy, Is.False, "ouvert d'avance");
            icone.onClick.Invoke(); Canvas.ForceUpdateCanvases(); Assert.That(gestes.Panneau.gameObject.activeInHierarchy, Is.True, "fermé au premier clic");
            icone.onClick.Invoke(); Assert.That(gestes.Panneau.gameObject.activeInHierarchy, Is.False, "ouvert au second clic");
            icone.onClick.Invoke(); Canvas.ForceUpdateCanvases();
            // Rapporté à la toile de 1920 × 1080 : le feuillet est posé en (24, 124), le panneau à 764 de lui.
            Rect page = Locale(gestes.Panneau); page.x += Locale(feuillet).x; page.y += Locale(feuillet).y;
            Assert.That(page.xMin >= 788 && page.xMax <= 1288 && page.yMin >= 124 && page.yMax <= 764, Is.True, "le panneau " + page + " sort de x 788-1288, y 124-764");
            foreach (string nom in new[] { "Votre maison", "Territoire conservé", "FORGE · Le cabinet" })
                Assert.That(page.Overlaps(Locale((RectTransform)toile.Find(nom))), Is.False, "le panneau recouvre « " + nom + " »");
            var lecture = feuillet.Find("Lecture défilante"); Assert.That(page.Overlaps(new Rect(Locale(feuillet).x + Locale((RectTransform)lecture).x, Locale(feuillet).y + Locale((RectTransform)lecture).y, 692, 620)), Is.False, "le panneau recouvre la lecture du feuillet");
            var contenus = gestes.Panneau.Cast<Transform>().Where(t => (t.GetComponent<Text>() != null || t.GetComponent<Button>() != null) && t.name != "Filet" && t.name != GestesDesJauges.TITRE).Cast<RectTransform>().ToArray();
            Assert.That(contenus.Length, Is.GreaterThanOrEqualTo(8), "état, deux textes, deux gestes, message, retour et confirmer");
            for (int i = 0; i < contenus.Length; i++)
            {
                Rect a = Locale(contenus[i]); Assert.That(a.xMin >= 0 && a.xMax <= 500 && a.yMax <= 640, Is.True, contenus[i].name + " sort du panneau : " + a);
                for (int j = i + 1; j < contenus.Length; j++) Assert.That(a.Overlaps(Locale(contenus[j])), Is.False, contenus[i].name + " recouvre " + contenus[j].name);
            }
            gestes.Pas(); Assert.That(gestes.EtatAffiche, Is.EqualTo("Choisissez une maison pour dépenser ses points."));
            Assert.That(gestes.Panneau.GetComponentsInChildren<Button>(true).Where(b => b.interactable).Select(b => b.name), Is.Empty, "un bouton actif sans maison");
        }

        // La carte va d'un bord à l'autre de l'écran : sa caméra le couvre tout, même une caméra de scène qui en gardait une part,
        // et aucun fond de colonne n'est posé sur elle.
        [Test] public void La_camera_de_la_carte_couvre_tout_l_ecran()
        {
            var dessinee = racine.GetComponent<CarteDessinee>(); var scene = new GameObject("caméra de scène").AddComponent<Camera>(); var texture = new RenderTexture(1920, 1080, 16);
            try
            {
                scene.targetTexture = texture; scene.rect = new Rect(0, 0, .67f, 1); dessinee.camera = scene; cabinet.Afficher();
                Assert.That(scene.rect, Is.EqualTo(new Rect(0, 0, 1, 1)), "la caméra de la carte ne couvre pas tout l'écran");
                Assert.That(racine.transform.Find("Cabinet/Fond des dossiers"), Is.Null, "le fond de la colonne de droite est encore posé");
                foreach (var ici in new[] { new Vector2(960, 540), new Vector2(1900, 540), new Vector2(1300, 1060), new Vector2(1919, 1079), new Vector2(2, 2) })
                    Assert.That(cabinet.HorsCarte(ici), Is.False, "le point " + ici + " de l'écran est hors de la carte");
                Assert.That(cabinet.HorsCarte(new Vector2(2000, 540)), Is.True, "contre-épreuve : un point hors de l'écran est sur la carte");
            }
            finally { dessinee.camera = null; scene.targetTexture = null; Object.DestroyImmediate(texture); Object.DestroyImmediate(scene.gameObject); }
        }

        // Les panneaux de la toile ouverts, par leur nom ; le bandeau du haut n'en est pas un.
        static string[] Ouverts(Transform toile) => toile.Cast<Transform>().Where(t => t.name != "FORGE · Le cabinet" && t.Find("Filet") != null && t.gameObject.activeSelf).Select(t => t.name).OrderBy(n => n, StringComparer.Ordinal).ToArray();
        Button IconeDeLaMaison() => racine.transform.Find("Cabinet/FORGE · Le cabinet/" + CabinetDeCarte.DOSSIERS).GetComponentsInChildren<Button>(true).Single(b => b.name == "Votre maison");
        // Hors l'accueil, rien ne s'ouvre sans le clic du joueur : la maison servie ne pose aucun panneau sur la carte (l'encart des
        // premiers gestes, ouvert par « Commencer », mis à part), une terre gardée n'ouvre que sa fiche, l'icône à écu ouvre « Votre maison ».
        [Test] public void Aucun_panneau_ne_s_ouvre_sans_un_clic_hors_l_accueil()
        {
            Proposer(); Transform toile = racine.transform.Find("Cabinet");
            Assert.That(Ouverts(toile), Is.EqualTo(new[] { AccueilDuPays.TITRE }), "à l'ouverture, d'autres panneaux que l'accueil sont ouverts");
            Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); cabinet.Afficher();
            Assert.That(cabinet.Accueil.Ouvert, Is.False, "l'accueil reste ouvert sur une maison servie");
            Assert.That(Ouverts(toile).Where(n => n != PremiersGestes.TITRE), Is.Empty, "maison servie, un panneau s'ouvre sans clic");
            cabinet.Garder(Terre(7, "Ville test")); cabinet.Afficher();
            Assert.That(Ouverts(toile).Where(n => n != PremiersGestes.TITRE), Is.EqualTo(new[] { "Territoire conservé" }), "une terre gardée n'ouvre pas sa seule fiche");
            IconeDeLaMaison().onClick.Invoke(); cabinet.Afficher();
            Assert.That(Ouverts(toile).Where(n => n != PremiersGestes.TITRE), Is.EqualTo(new[] { "Territoire conservé", "Votre maison" }), "l'icône à écu n'ouvre pas « Votre maison »");
            IconeDeLaMaison().onClick.Invoke(); cabinet.Afficher(); Assert.That(toile.Find("Votre maison").gameObject.activeSelf, Is.False, "le second clic sur l'icône ne ferme pas « Votre maison »");
            cabinet.Relacher(); cabinet.Afficher(); Assert.That(Ouverts(toile).Where(n => n != PremiersGestes.TITRE), Is.Empty, "la fiche reste ouverte sans terre gardée");
        }

        // Chaque panneau qu'un clic ouvre porte la croix du socle, et la croix le ferme pour de bon : l'image suivante ne le rouvre pas.
        [Test] public void Chaque_panneau_ouvert_a_sa_croix()
        {
            try
            {
                Publier(JOUEUR, new LieuTenu(10, 0)); cabinet.Afficher(); cabinet.Garder(Terre(7, "Ville test")); cabinet.Afficher(); Transform toile = racine.transform.Find("Cabinet");
                var panneaux = toile.Cast<Transform>().Where(t => t.name != "FORGE · Le cabinet" && t.name != AccueilDuPays.TITRE && t.name != "Menu du cabinet" && t.Find("Filet") != null).Cast<RectTransform>().ToArray();
                Assert.That(panneaux.Select(p => p.name), Is.SupersetOf(new[] { "Votre maison", "Territoire conservé", "Plan du bourg", "Terres et comptes", "Les autres maisons", DossierPays.TITRE, DossierGuerre.TITRE, PremiersGestes.TITRE, "Les chantiers du bourg" }));
                foreach (var panneau in panneaux)
                {
                    Button croix = SocleInterfaceTests.CroixDe(panneau); Assert.That(croix, Is.Not.Null, "« " + panneau.name + " » n'a pas sa croix");
                    panneau.gameObject.SetActive(true); croix.onClick.Invoke(); Assert.That(panneau.gameObject.activeSelf, Is.False, "la croix ne ferme pas « " + panneau.name + " »");
                    cabinet.Afficher(); Assert.That(panneau.gameObject.activeSelf, Is.False, "« " + panneau.name + " » se rouvre après sa croix");
                }
                Assert.That(cabinet.Retenue, Is.Null, "la croix de la fiche garde la terre");
            }
            finally { PremiersGestes.OublierLesFermetures(); }
        }

        // « Ma capitale » ramène la vue sur le siège servi de la maison du joueur, où que le joueur l'ait menée ; sans maison, ou
        // sans siège placé, elle ne se montre pas.
        [Test] public void Ma_capitale_recentre_sur_le_siege_servi()
        {
            Preparer(); partie = new LecturePartie(() => null, _ => null, () => null, _ => null); cabinet.Partie = partie;
            void Servir(string id, PointCarte? siege)
            {
                Poser(partie, "Monde", MondeDe(id));
                Poser(partie, "Maison", Lecture<MaisonLue>.De(new MaisonLue(id, "Maison", new SiegeDeMaison(10, 0, "Siège", siege), new[] { new LieuTenu(10, 0) }, new Dictionary<string, string>())));
                cabinet.Afficher();
            }
            Vector2 Attendu(PointCarte p) { Vector3 ici = carte.PositionSurLaCarte(p, 0f).Value; return new Vector2(ici.x, ici.z); }
            Poser(partie, "Monde", MondeDe(null)); cabinet.Afficher();
            Button capitale = racine.GetComponentsInChildren<Button>(true).Single(b => b.name == "Ma capitale");
            Assert.That(capitale.gameObject.activeSelf, Is.False, "« Ma capitale » se montre sans maison");
            Servir(JOUEUR, null); Assert.That(capitale.gameObject.activeSelf, Is.False, "« Ma capitale » se montre pour un siège sans position");
            var siege = new PointCarte(3001000, 1502000); Servir(JOUEUR, siege); Assert.That(capitale.gameObject.activeSelf, Is.True, "« Ma capitale » cachée avec un siège placé");
            string phrase = capitale.GetComponent<Infobulle>()?.Phrase; Assert.That(!string.IsNullOrWhiteSpace(phrase) && phrase != capitale.name, Is.True, "« " + phrase + " »");
            carte.Vue.Centrer(new Vector2(-500, 300), 900); cabinet.Afficher(); Assert.That(carte.Vue.Centre, Is.EqualTo(new Vector2(-500, 300)), "la vue est reprise au joueur sans clic");
            capitale.onClick.Invoke();
            Assert.That(Vector2.Distance(carte.Vue.Centre, Attendu(siege)), Is.LessThan(1e-3f), "la vue ne revient pas sur le siège : " + carte.Vue.Centre);
            Assert.That(carte.Vue.Demi, Is.EqualTo(CabinetDeCarte.DEMI_SUR_LE_SIEGE_KM).Within(1e-3f)); Assert.That(camera.transform.position, Is.EqualTo(carte.Vue.Position), "la caméra n'est pas posée sur la vue");
            var autre = new PointCarte(2999000, 1499000); Servir(B, autre); carte.Vue.Centrer(new Vector2(-500, 300), 900); capitale.onClick.Invoke();
            Assert.That(Vector2.Distance(carte.Vue.Centre, Attendu(autre)), Is.LessThan(1e-3f), "la vue ne suit pas le siège servi de la maison : " + carte.Vue.Centre);
            Assert.That(Vector2.Distance(Attendu(autre), Attendu(siege)), Is.GreaterThan(1f), "contre-épreuve : les deux sièges se confondent");
        }
    }
}
