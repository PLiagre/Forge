using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Lot #625 — un repère par terre de départ servie, sur le siège que `/maison` donne. Le faux service sert la carte et les départs de
    // la graine 0, et pour chaque maison une fiche écrite ici d'après les sièges mesurés (graine 0, tick 3), remplaçable ; il note chaque requête.
    public sealed class ReperesDeDepartTests {
        private const int ATTENTE_MS = 30000, DELAI_MAX_PAS_MS = 100, LENTEUR_MS = 2000; private const string MOREE = "Despotat de Morée", RACINE = "Repères des terres de départ";
        private static readonly (long id, string maison, long cell, string siege, double x, double y)[] SIEGES = {
            (1, "Bar", 10430, "Bar-le-Duc", 3965409.11, 2862646.57), (2, "Wurtemberg", 10465, "Stuttgart", 4260932.34, 2851742.83),
            (3, "Paléologue", 10340, "Mistra", 5424441.58, 1644956.82), (4, "Branković", 10334, "Vučitrn", 5217097.38, 2256208.68),
            (5, "Evrenosoğulları", 10337, "Giannitsa", 5367717.15, 2051967.94), (6, "Banou Mozni", 10103, "Biskra", 3926430.32, 1322273.47) };
        private int port; private volatile int statutDeparts, lenteurDeparts; private HttpListener ecoute; private Thread fil; private readonly List<string> recues = new List<string>();
        private readonly ConcurrentDictionary<string, (int statut, string corps)> maisons = new ConcurrentDictionary<string, (int, string)>();
        private volatile int lenteurIntention; private readonly List<string> deposes = new List<string>(); // lot #613 : chaque corps de `POST /intention`
        private readonly ConcurrentQueue<(int statut, string corps)> reponses = new ConcurrentQueue<(int, string)>(); // rendues dans l'ordre, 404 une fois vide
        private GameObject objet; private CarteDessinee carte; private ReperesDeDepart reperes;
        private static byte[] Fixture(string nom) => File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/" + nom);
        [SetUp] public void PortLibre() {
            var sonde = new TcpListener(IPAddress.Loopback, 0); sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop();
            statutDeparts = 200; lenteurDeparts = lenteurIntention = 0; lock (recues) { recues.Clear(); deposes.Clear(); } while (reponses.TryDequeue(out _)) { } maisons.Clear(); foreach (var s in SIEGES) maisons["/maison?id=seigneurie-" + s.id] = (200, Fiche(s));
        }
        [TearDown] public void Fermer() { reperes?.Arreter(); carte?.Arreter(); if (objet != null) UnityEngine.Object.DestroyImmediate(objet); ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }
        private static string Fiche((long id, string maison, long cell, string siege, double x, double y) s) =>
            "{\"id\":\"seigneurie-" + s.id + "\",\"nom\":\"" + s.maison + "\",\"siege\":{\"cell_id\":" + s.cell + ",\"rang\":0,\"nom\":\"" + s.siege + "\",\"point\":{\"x_m\":"
            + s.x.ToString("R", CultureInfo.InvariantCulture) + ",\"y_m\":" + s.y.ToString("R", CultureInfo.InvariantCulture) + "}},\"lieux\":["
            + string.Join(",", Enumerable.Range(0, 4).Select(r => "{\"cell_id\":" + s.cell + ",\"rang\":" + r + "}")) + "],\"absents\":{}}";
        private void Servir() {
            byte[] carteServie = Fixture("carte-graine0.json"), departsServis = Fixture("departs-graine0-tick3.json");
            var auditeur = ecoute = new HttpListener(); auditeur.Prefixes.Add("http://127.0.0.1:" + port + "/"); auditeur.Start();
            (fil = new Thread(() => {
                try { while (true) {
                    HttpListenerContext ctx = auditeur.GetContext(); string ici = ctx.Request.Url.PathAndQuery; lock (recues) recues.Add(ici); if (ici == "/departs") Thread.Sleep(lenteurDeparts);
                    string depose = ici == "/intention" ? new StreamReader(ctx.Request.InputStream, Encoding.UTF8).ReadToEnd() : null;
                    if (depose != null) { lock (recues) deposes.Add(depose); Thread.Sleep(lenteurIntention); }
                    var (statut, corps) = depose != null ? (reponses.TryDequeue(out var r) ? (r.statut, Encoding.UTF8.GetBytes(r.corps)) : (404, Encoding.UTF8.GetBytes("{\"erreur\":\"aucune réponse prévue\"}")))
                        : ici == "/carte" ? (200, carteServie) : ici == "/departs" ? (statutDeparts, statutDeparts == 200 ? departsServis : Encoding.UTF8.GetBytes("{\"erreur\":\"panne\"}"))
                        : maisons.TryGetValue(ici, out var m) ? (m.statut, Encoding.UTF8.GetBytes(m.corps)) : (404, Encoding.UTF8.GetBytes("{\"erreur\":\"maison inconnue\"}"));
                    ctx.Response.StatusCode = statut; ctx.Response.Close(corps, true);
                } } catch (Exception) { }
            }) { IsBackground = true }).Start();
        }
        private int Recues(string chemin = null) { lock (recues) return recues.Count(r => chemin == null || r == chemin); }
        // Ce que le service sert, lu par les clients du pont avant de poser les composants ; les requêtes repartent de zéro.
        private IReadOnlyList<FicheDeDepart> Lues(out PointCarte origine) {
            LectureCarte lue; Lecture<DepartsLus> departs;
            using (var c = new ClientCarte(port, ClientCarte.DelaiMinimal)) lue = c.Lire(); using (var d = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) departs = d.Lire();
            Assert.IsTrue(lue.Presente && departs.Presente, lue.Absence + " " + departs.Absence);
            origine = MaillageDeCarte.Mailler(lue.Carte).Origine; lock (recues) recues.Clear(); return departs.Donnees.Fiches;
        }
        private void Poser() { objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>(); carte.port = port; carte.Demarrer(); reperes = objet.AddComponent<ReperesDeDepart>(); reperes.port = port; reperes.Demarrer(); }
        // Des pas au même instant jusqu'à la carte posée et la lecture des repères finie, puis un pas qui l'applique.
        private void Avancer(double t) {
            var montre = Stopwatch.StartNew(); do { carte.Pas(t); reperes.Pas(t); Thread.Sleep(10); } while ((carte.CellulesServies < 0 || carte.LectureEnVol || reperes.LectureEnVol) && montre.ElapsedMilliseconds < ATTENTE_MS);
            Assert.IsFalse(reperes.LectureEnVol, "la lecture des repères n'a pas fini"); reperes.Pas(t);
        }
        private int Nommes(string nom) => objet.GetComponentsInChildren<Transform>(true).Count(t => t.name == nom);
        private long? Sous(double x, double z) => carte.CelluleSous(objet.transform.TransformPoint(new Vector3((float)x, 0, (float)z)))?.CellId;
        private static bool Egal(Vector3 a, Vector3 b) => a.x == b.x && a.y == b.y && a.z == b.z;
        [Test] public void Six_reperes_chacun_dans_la_cellule_de_sa_terre() {
            Servir(); IReadOnlyList<FicheDeDepart> fiches = Lues(out PointCarte o); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Avancer(1); var cellules = new HashSet<long>();
            Assert.IsTrue(fiches.Count == 6 && reperes.ReperesPoses == fiches.Count && ReperesDeDepart.HAUTEUR_REPERE > CarteDessinee.HAUTEUR_NOM, reperes.ReperesPoses + " repères pour " + fiches.Count + " fiches : " + reperes.TexteAffiche);
            foreach (FicheDeDepart f in fiches) {
                int i = Array.FindIndex(SIEGES, x => x.id == f.Id); var s = SIEGES[i]; var suivant = SIEGES[(i + 1) % SIEGES.Length];
                Transform r = objet.transform.Find(RACINE + "/Repère " + f.Nom); Assert.IsTrue(r != null && Nommes("Repère " + f.Nom) == 1, "pas un seul repère pour " + f.Nom);
                Vector3 attendu = new Vector3((float)((s.x - o.X) / 1000), ReperesDeDepart.HAUTEUR_REPERE, (float)((s.y - o.Y) / 1000));
                Assert.IsTrue(Egal(r.localPosition, attendu), f.Nom + " en " + r.localPosition.ToString("R") + ", attendu " + attendu.ToString("R"));
                Assert.AreEqual(f.CellId, carte.CelluleSous(r.position)?.CellId, f.Nom + " hors de la cellule de sa terre");
                Assert.AreEqual((Color32)ReperesDeDepart.COULEUR_REPERE, (Color32)r.Find("Disque").GetComponent<MeshRenderer>().sharedMaterial.color, f.Nom);
                // Contre-épreuves : le siège suivant, ce siège sans origine ou pris en (lat, lon), ne sont pas dans cette cellule.
                Assert.AreNotEqual(f.CellId, Sous((suivant.x - o.X) / 1000, (suivant.y - o.Y) / 1000), f.Nom + " : le siège suivant tombe dans sa cellule");
                Assert.AreNotEqual(f.CellId, Sous(s.x / 1000, s.y / 1000), f.Nom + " : sans origine, encore dans sa cellule");
                Assert.AreNotEqual(f.CellId, Sous(f.Siege.Lat, f.Siege.Lon), f.Nom + " : en (lat, lon), encore dans sa cellule");
                cellules.Add(f.CellId); Assert.AreEqual(1, Recues("/maison?id=seigneurie-" + f.Id), f.Nom);
            }
            MeshRenderer[] posees = objet.transform.Find("Cellules de la carte").GetComponentsInChildren<MeshRenderer>();
            Assert.IsTrue(cellules.Count == 6 && posees.Length == 596 && posees.All(m => m.sharedMaterial.color != ReperesDeDepart.COULEUR_REPERE), "des terres partagent une cellule, ou une cellule a la couleur des repères");
            Assert.IsTrue(Recues("/departs") == 1 && Recues() == 2 + fiches.Count && reperes.TexteAffiche == null, Recues() + " requêtes ; " + reperes.TexteAffiche);
            for (int i = 1; i <= 20; i++) { carte.Pas(1 + 3 * i); reperes.Pas(1 + 3 * i); Assert.IsFalse(reperes.LectureEnVol, "une lecture repart à " + (1 + 3 * i) + " s"); }
            Thread.Sleep(100); Assert.IsTrue(Recues() == 2 + fiches.Count && reperes.ReperesPoses == 6, Recues() + " requêtes après vingt pas");
        }
        [TestCase("statut 404")] [TestCase("siège hors carte, ")]
        public void Une_maison_absente_se_dit_sans_repere(string cause) {
            const string raison = "siège sans cellule sur la carte servie", demande = "/maison?id=seigneurie-3"; string vraie = maisons[demande].corps;
            maisons[demande] = cause == "statut 404" ? (404, "{\"erreur\":\"maison inconnue\"}")
                : (200, "{\"id\":\"seigneurie-3\",\"nom\":\"Paléologue\",\"siege\":{\"cell_id\":null,\"rang\":null,\"nom\":\"Mistra\",\"point\":null},\"lieux\":[],\"absents\":{\"siege\":\"" + raison + "\"}}");
            Servir(); Lues(out _); Poser(); Avancer(1);
            Assert.IsTrue(reperes.ReperesPoses == 5 && Nommes("Repère " + MOREE) == 0, reperes.ReperesPoses + " repères");
            StringAssert.StartsWith(ReperesDeDepart.MESSAGE_ABSENCE + "\n" + MOREE + " : ", reperes.TexteAffiche);
            StringAssert.Contains(cause == "statut 404" ? "maison : statut 404" : cause + raison, reperes.TexteAffiche);
            Transform racine = objet.transform.Find(RACINE); Transform[] avant = Enumerable.Range(0, 5).Select(racine.GetChild).ToArray();
            maisons[demande] = (200, vraie); reperes.Pas(2); Assert.IsFalse(reperes.LectureEnVol, "une lecture repart 1 s après l'absence");
            Avancer(1 + ReperesDeDepart.PERIODE_RELECTURE_S);
            Assert.IsTrue(reperes.ReperesPoses == 6 && racine.childCount == 6 && Nommes("Repère " + MOREE) == 1 && reperes.TexteAffiche == null, reperes.ReperesPoses + " repères ; " + reperes.TexteAffiche);
            for (int i = 0; i < 5; i++) Assert.AreSame(avant[i], racine.GetChild(i), "un repère déjà posé a été refait");
            Assert.IsTrue(Recues("/departs") == 2 && Recues(demande) == 2 && Recues("/maison?id=seigneurie-1") == 1, Recues() + " requêtes");
        }
        [Test] public void Sans_departs_aucun_repere_et_aucune_maison_demandee() {
            Servir(); Lues(out _); statutDeparts = 500; Poser(); Avancer(1);
            Assert.IsTrue(reperes.ReperesPoses == 0 && objet.transform.Find(RACINE) == null && Recues("/departs") == 1 && Recues() == 2, reperes.ReperesPoses + " repères, " + Recues() + " requêtes");
            StringAssert.StartsWith(ReperesDeDepart.MESSAGE_ABSENCE + "\ndeparts : statut 500", reperes.TexteAffiche);
        }
        [Test] public void Le_pas_n_attend_pas_les_departs() {
            Servir(); Lues(out _); lenteurDeparts = LENTEUR_MS; Poser();
            reperes.Pas(1); Assert.IsFalse(reperes.LectureEnVol, "une lecture part avant que la carte soit posée");
            var attente = Stopwatch.StartNew(); while (carte.CellulesServies < 0 && attente.ElapsedMilliseconds < ATTENTE_MS) { carte.Pas(1); Thread.Sleep(10); }
            Assert.IsTrue(carte.CellulesServies > 0 && Recues("/departs") == 0, carte.TexteAffiche);
            var montre = Stopwatch.StartNew(); reperes.Pas(1); montre.Stop(); Assert.Less(montre.ElapsedMilliseconds, DELAI_MAX_PAS_MS, "le pas a attendu le service"); Assert.IsTrue(reperes.LectureEnVol);
        }
        // Lot #624 — la fiche d'une terre au survol de son repère, telle que le faux service la sert.
        private const string FICHE_MOREE = "Despotat de Morée\nMaison : Paléologue\nSiège : Mistra, cellule 10340\nHabitants de la cellule : 80919 au tick 3\nSuzerain : Byzance\nVoisins :\n"
            + "  cellule 10335, Byzance, 77525 habitants\n  cellule 10347, Byzance, 55393 habitants\nLieux tenus : 4";
        private Transform Repere(FicheDeDepart f) => objet.transform.Find(RACINE + "/Repère " + f.Nom);
        private MaisonLue Maison(long id) { using (var m = new ClientMaison(port, ClientDeparts.DelaiMinimal)) { var l = m.Lire("seigneurie-" + id); Assert.IsTrue(l.Presente, l.Absence); return l.Donnees; } }
        [Test] public void Le_survol_d_un_repere_ouvre_la_fiche_servie_de_sa_terre() {
            Servir(); IReadOnlyList<FicheDeDepart> fiches = Lues(out _); var lues = fiches.ToDictionary(f => f.Id, f => Maison(f.Id)); Poser(); Avancer(1); string zab = null;
            Assert.IsTrue(fiches.Count == 6 && reperes.ReperesPoses == 6 && reperes.FicheAffichee == null, reperes.ReperesPoses + " repères ; fiche « " + reperes.FicheAffichee + " »");
            foreach (FicheDeDepart f in fiches) {
                Transform r = Repere(f); reperes.SurvolerPoint(r.position); string vu = reperes.FicheAffichee;
                Assert.IsTrue(reperes.Survolee?.Id == f.Id && vu == ReperesDeDepart.Decrire(f, 3, lues[f.Id]), f.Nom + " : « " + vu + " »");
                foreach (string attendu in new[] { f.Nom + "\n", "\nMaison : " + f.Maison + "\n", "\nSiège : " + f.Siege.Nom + ", cellule " + f.CellId + "\n", " " + f.Habitants + " au tick 3\n",
                    "\nSuzerain : " + (f.Suzerain?.Nom ?? "aucun, le monde n'en nomme pas") + "\n", "\nLieux tenus : 4" }.Concat(f.Voisins.Select(v => "\n  cellule " + v.CellId + ", ")))
                    StringAssert.Contains(attendu, vu, f.Nom);
                reperes.Quitter(); reperes.Survoler(carte.camera.WorldToScreenPoint(r.position)); Assert.IsTrue(reperes.Survolee?.Id == f.Id && reperes.FicheAffichee == vu, f.Nom + " par l'écran : « " + reperes.FicheAffichee + " »");
                if (f.Nom == MOREE) Assert.AreEqual(FICHE_MOREE, vu); if (f.Siege.Nom == "Biskra") zab = vu;
            }
            Assert.IsTrue(zab != null && zab != FICHE_MOREE && zab.Contains("\nSuzerain : Hafsides\n") && zab.Contains("\n  cellule 10087, aucune puissance nommée, 5509 habitants\n")
                && zab.Split('\n').Count(l => l.StartsWith("  cellule ")) == 7, "Zab : « " + zab + " »");
        }
        [Test] public void La_fiche_compte_les_lieux_servis() {
            const string demande = "/maison?id=seigneurie-3"; string deux = maisons[demande].corps.Replace(",{\"cell_id\":10340,\"rang\":2},{\"cell_id\":10340,\"rang\":3}", "");
            Assert.AreNotEqual(maisons[demande].corps, deux); maisons[demande] = (200, deux);
            Servir(); FicheDeDepart moree = Lues(out _).Single(f => f.Nom == MOREE); Poser(); Avancer(1);
            reperes.SurvolerPoint(Repere(moree).position); StringAssert.EndsWith("\nLieux tenus : 2", reperes.FicheAffichee);
        }
        [Test] public void Hors_d_un_repere_la_fiche_se_cache() {
            Servir(); FicheDeDepart moree = Lues(out _).Single(f => f.Nom == MOREE); Poser(); objet.transform.position = new Vector3(1000, 50, -2000); Avancer(1);
            Vector3 centre = Repere(moree).localPosition; Vector3 Decale(float k) => objet.transform.TransformPoint(centre + new Vector3(k * ReperesDeDepart.DIAMETRE_REPERE_KM, 0, 0));
            reperes.SurvolerPoint(Decale(0.45f)); Assert.IsTrue(reperes.Survolee?.Nom == MOREE && reperes.FicheAffichee != null && reperes.FicheAffichee.StartsWith(MOREE + "\n"), "à 0,45 diamètre : « " + reperes.FicheAffichee + " »");
            reperes.SurvolerPoint(Decale(0.55f)); Assert.IsTrue(reperes.Survolee == null && reperes.FicheAffichee == null, "à 0,55 diamètre : « " + reperes.FicheAffichee + " »");
            reperes.SurvolerPoint(Decale(0)); reperes.SurvolerPoint(new Vector3(1e6f, 0, 1e6f)); Assert.IsTrue(reperes.Survolee == null && reperes.FicheAffichee == null, "en mer : « " + reperes.FicheAffichee + " »");
            reperes.SurvolerPoint(Decale(0)); Assert.IsNotNull(reperes.FicheAffichee); reperes.Quitter(); Assert.IsTrue(reperes.Survolee == null && reperes.FicheAffichee == null, "après Quitter : « " + reperes.FicheAffichee + " »");
        }
        [Test] public void La_fiche_de_la_terre_tient_le_coin_bas_droit() {
            Servir(); Lues(out _); Poser(); var cellule = objet.AddComponent<FicheDeCellule>(); cellule.port = port; cellule.Demarrer();
            try {
                Avancer(1); RectTransform[] cadres = objet.GetComponentsInChildren<RectTransform>(true);
                RectTransform terre = cadres.Single(t => t.name == "Fiche de la terre"), fiche = cadres.Single(t => t.name == "Fiche"), absences = cadres.Single(t => t.name == "Absences");
                Assert.IsTrue(terre.anchorMin == Vector2.right && terre.anchorMax == Vector2.right && terre.pivot == Vector2.right, "fiche de la terre ancrée en " + terre.anchorMin + "–" + terre.anchorMax + ", pivot " + terre.pivot);
                Assert.IsTrue(fiche.anchorMin == Vector2.zero && absences.anchorMin == Vector2.up && fiche.anchorMin != terre.anchorMin && absences.anchorMin != terre.anchorMin, fiche.anchorMin + " " + absences.anchorMin);
                // UnityEngine.UI n'est pas référencé ici : raycastTarget se lit sur chaque graphique (l'image et le texte) par son nom.
                var cibles = terre.GetComponentsInChildren<Component>(true).Select(c => c.GetType().GetProperty("raycastTarget")?.GetValue(c)).Where(v => v != null).ToList();
                Assert.IsTrue(cibles.Count == 2 && cibles.All(v => (bool)v == false), cibles.Count + " graphiques, raycastTarget " + string.Join(", ", cibles));
            } finally { cellule.Arreter(); }
        }
        // Lot #613 — un clic sur un repère dépose le choix de sa terre ; l'écran dit le reçu du faux service tel quel.
        private const string ZAB = "Émirat du Zab", CHOIX_MOREE = "{\"type\":\"choisir_depart\",\"seigneurie\":3}", CHOIX_ZAB = "{\"type\":\"choisir_depart\",\"seigneurie\":6}";
        private string[] Deposes() { lock (recues) return deposes.ToArray(); }
        private Vector2 Ecran(string nom) => carte.camera.WorldToScreenPoint(objet.transform.Find(RACINE + "/Repère " + nom).position);
        private void Finir() {
            var montre = Stopwatch.StartNew(); while (reperes.ChoixEnVol && montre.ElapsedMilliseconds < ATTENTE_MS) { reperes.Pas(1); Thread.Sleep(10); }
            Assert.IsFalse(reperes.ChoixEnVol, "le dépôt n'a pas fini");
        }
        private void Cliquer(string nom) { reperes.Choisir(Ecran(nom)); Finir(); }
        private void Prets(params (int statut, string corps)[] file) { Servir(); Lues(out _); Poser(); Avancer(1); foreach (var r in file) reponses.Enqueue(r); }
        [Test] public void Un_clic_depose_le_choix_de_sa_terre() {
            Prets((200, "{\"acceptee\":true,\"appliquee_au_tick\":7}")); Cliquer(MOREE);
            Assert.IsTrue(Recues("/intention") == 1 && Deposes().SequenceEqual(new[] { CHOIX_MOREE }), Recues("/intention") + " dépôts : " + string.Join(" ; ", Deposes()));
            Assert.IsTrue(reperes.TerreDuChoix?.Nom == MOREE && reperes.RecuDuChoix?.AppliqueeAuTick == 7, reperes.TerreDuChoix?.Nom + " au tick " + reperes.RecuDuChoix?.AppliqueeAuTick);
            Assert.AreEqual("Terre choisie : Despotat de Morée\nLe monde l'applique au tick suivant (après le tick 7).", reperes.ChoixAffiche);
        }
        [Test] public void Le_second_choix_affiche_le_refus_du_service() {
            Prets((200, "{\"acceptee\":true,\"appliquee_au_tick\":3}"), (409, "{\"acceptee\":false,\"erreur\":\"départ déjà choisi : seigneurie-3\"}"),
                (400, "{\"acceptee\":false,\"erreur\":\"raison du faux service\"}"));
            Cliquer(MOREE); Cliquer(ZAB);
            Assert.IsTrue(Deposes().SequenceEqual(new[] { CHOIX_MOREE, CHOIX_ZAB }), string.Join(" ; ", Deposes()));
            Assert.IsTrue(reperes.TerreDuChoix?.Nom == ZAB && reperes.RecuDuChoix?.Statut == 409, reperes.TerreDuChoix?.Nom + ", statut " + reperes.RecuDuChoix?.Statut);
            Assert.AreEqual("Choix refusé pour Émirat du Zab :\ndépart déjà choisi : seigneurie-3", reperes.ChoixAffiche);
            // Contre-épreuve : une autre raison du service s'affiche aussi mot pour mot.
            Cliquer(ZAB); Assert.IsTrue(Recues("/intention") == 3 && reperes.RecuDuChoix?.Statut == 400, Recues("/intention") + " dépôts, statut " + reperes.RecuDuChoix?.Statut);
            Assert.AreEqual("Choix refusé pour Émirat du Zab :\nraison du faux service", reperes.ChoixAffiche);
        }
        [Test] public void Hors_d_un_repere_rien_et_sans_reponse_l_absence_se_dit() {
            Prets(); reperes.Choisir(carte.camera.WorldToScreenPoint(objet.transform.TransformPoint(new Vector3(1e6f, 0, 1e6f)))); Finir();
            Assert.IsTrue(Recues("/intention") == 0 && reperes.TerreDuChoix == null && reperes.ChoixAffiche == null, Recues("/intention") + " dépôts ; « " + reperes.ChoixAffiche + " »");
            Cliquer(MOREE); RecuIntention recu = reperes.RecuDuChoix;
            Assert.IsTrue(Recues("/intention") == 1 && recu != null && !recu.Presente && recu.Absence.StartsWith("intention : statut 404"), Recues("/intention") + " dépôts ; " + recu?.Absence);
            Assert.AreEqual("Choix sans réponse pour Despotat de Morée :\n" + recu.Absence, reperes.ChoixAffiche);
        }
        [Test] public void Le_pas_n_attend_pas_le_choix() {
            Prets((200, "{\"acceptee\":true,\"appliquee_au_tick\":3}")); lenteurIntention = LENTEUR_MS;
            var montre = Stopwatch.StartNew(); reperes.Choisir(Ecran(MOREE)); reperes.Pas(1); montre.Stop();
            Assert.Less(montre.ElapsedMilliseconds, DELAI_MAX_PAS_MS, "le clic ou le pas a attendu le service"); Assert.IsTrue(reperes.ChoixEnVol, "aucun dépôt en vol");
            Assert.AreEqual("Choix envoyé au monde : Despotat de Morée", reperes.ChoixAffiche);
            reperes.Choisir(Ecran(ZAB)); Finir();
            Assert.IsTrue(Recues("/intention") == 1 && Deposes().SequenceEqual(new[] { CHOIX_MOREE }) && reperes.TerreDuChoix?.Nom == MOREE, Recues("/intention") + " dépôts : " + string.Join(" ; ", Deposes()));
            RectTransform choix = objet.GetComponentsInChildren<RectTransform>(true).Single(t => t.name == "Choix de la terre"); Vector2 haut = new Vector2(0.5f, 1);
            Assert.IsTrue(choix.anchorMin == haut && choix.anchorMax == haut && choix.pivot == haut, "choix ancré en " + choix.anchorMin + "–" + choix.anchorMax + ", pivot " + choix.pivot);
            var cibles = choix.GetComponentsInChildren<Component>(true).Select(c => c.GetType().GetProperty("raycastTarget")?.GetValue(c)).Where(v => v != null).ToList();
            Assert.IsTrue(cibles.Count == 2 && cibles.All(v => (bool)v == false), cibles.Count + " graphiques, raycastTarget " + string.Join(", ", cibles));
        }
        // Un glissé qui dépasse le seuil puis revient au point d'appui n'est pas un clic : l'écart final seul ne suffit pas.
        [Test] public void Un_glisse_qui_revient_au_depart_ne_choisit_pas() {
            var type = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("ForgeLocal3D.SurvolDeCarte")).First(t => t != null);
            object geste = Activator.CreateInstance(type.GetNestedType("GesteDeClic")); var noter = geste.GetType().GetMethod("Noter");
            bool G(float x, bool a, bool r) => (bool)noter.Invoke(geste, new object[] { new Vector2(x, 0f), a, r });
            Assert.IsFalse(G(0, true, false) || G(100, false, false) || G(0, false, true), "un détour de 100 px revenu au départ choisit encore");
            Assert.IsTrue(G(0, true, true) && !G(0, true, false) && !G(7, false, true), "un clic au même point doit choisir, un relâché à 7 px non");
        }
        // Lot #614 — la maison publiée descend au siège et pose un disque par lieu tenu. Le faux service inchangé sert aussi `/monde` et `/lieu`.
        private const long CELLULE_MOREE = 10340; private const string MAISON_MOREE = "seigneurie-3", DEMANDE_MOREE = "/maison?id=seigneurie-3";
        private FicheDeCellule fiche;
        private void Publier(string maison) => maisons["/monde"] = (200, "{\"tick\":4,\"date\":{\"annee\":1400,\"jour_de_l_annee\":4},\"cell_count\":1,\"cells\":[{\"cell_id\":10340,\"population\":1,\"hunger_ticks\":0,\"food_deficit_kg\":0}]" + (maison == null ? "}" : ",\"maison_du_joueur\":\"" + maison + "\"}"));
        private void ServirLieu(string corps) => maisons["/lieu?cell=" + CELLULE_MOREE] = (200, corps);
        private (long rang, double x, double y, string maitre)[] Quatre() { var s = SIEGES[2]; return new[] { (0L, s.x, s.y, MAISON_MOREE), (1L, s.x + 20000d, s.y, MAISON_MOREE), (2L, s.x, s.y + 22000d, MAISON_MOREE), (3L, s.x - 18000d, s.y - 16000d, MAISON_MOREE) }; }
        private (long rang, double x, double y, string maitre)[] AvecVoisin() { var s = SIEGES[2]; return Quatre().Concat(new[] { (4L, s.x + 90000d, s.y, "seigneurie-9") }).ToArray(); }
        private static string CorpsLieu(params (long rang, double x, double y, string maitre)[] pts) {
            string un((long rang, double x, double y, string maitre) p) => "{\"rang\":" + p.rang.ToString(CultureInfo.InvariantCulture) + ",\"point\":" + (double.IsNaN(p.x) ? "null" : "{\"x_m\":" + p.x.ToString("R", CultureInfo.InvariantCulture) + ",\"y_m\":" + p.y.ToString("R", CultureInfo.InvariantCulture) + "}") + ",\"maitre\":" + (p.maitre == null ? "null" : "\"" + p.maitre + "\"") + "}";
            return "{\"cell_id\":10340,\"tick\":4,\"date\":{\"annee\":1400,\"jour_de_l_annee\":4},\"population\":1,\"stocks\":{},\"hunger_ticks\":0,\"food_deficit_kg\":0,\"lieux\":[" + string.Join(",", pts.Select(un)) + "]}"; }
        private void Monter() { Servir(); Lues(out _); Poser(); carte.camera.aspect = 16f / 9f; fiche = objet.AddComponent<FicheDeCellule>(); fiche.port = port; fiche.Demarrer(); }
        private void Jusqua(double t, Func<bool> fini) { var montre = Stopwatch.StartNew(); do { carte.Pas(t); fiche.Pas(t); reperes.Pas(t); Thread.Sleep(10); } while (!fini() && montre.ElapsedMilliseconds < ATTENTE_MS); Assert.IsTrue(fini(), "« " + reperes.TexteAffiche + " » maison « " + fiche.MaisonDuJoueur + " »"); }
        private int DisquesActifs() => objet.GetComponentsInChildren<Transform>(true).Count(t => t.name == "Disque" && t.parent != null && t.parent.name.StartsWith("Lieu ") && t.gameObject.activeInHierarchy);
        private int DepartsActifs() { Transform r = objet.transform.Find(RACINE); return r == null ? 0 : r.Cast<Transform>().Count(c => c.gameObject.activeInHierarchy); }
        private Transform LieuPose(long rang) => objet.transform.Find(ReperesDeDepart.RACINE_LIEUX + "/" + ReperesDeDepart.NomDuLieu(CELLULE_MOREE, rang));
        [Test] public void La_maison_publiee_descend_sur_le_siege_et_ses_lieux() {
            var s = SIEGES[2]; Publier(null); ServirLieu(CorpsLieu(AvecVoisin())); Monter();
            Jusqua(1, () => reperes.ReperesPoses == 6 && fiche.MondeLu != null && fiche.MaisonDuJoueur == null);
            reponses.Enqueue((200, "{\"acceptee\":true,\"appliquee_au_tick\":4}")); Cliquer(MOREE); double apres = 2 + 2 * ReperesDeDepart.PERIODE_RELECTURE_S; for (double t = 2; t <= apres; t++) { carte.Pas(t); fiche.Pas(t); reperes.Pas(t); Thread.Sleep(50); }
            Assert.IsTrue(reperes.RecuDuChoix.Acceptee && DepartsActifs() == 6 && carte.Vue.Echelle == 1f && DisquesActifs() == 0 && Recues("/lieu?cell=" + CELLULE_MOREE) == 0 && Recues(DEMANDE_MOREE) == 1, Recues(DEMANDE_MOREE) + " lectures de la maison ; " + reperes.TexteAffiche);
            Publier(MAISON_MOREE); Jusqua(apres + 1, () => fiche.MaisonDuJoueur == MAISON_MOREE && DisquesActifs() == 4 && DepartsActifs() == 0);
            Assert.AreEqual(1, Recues("/lieu?cell=" + CELLULE_MOREE), "la cellule"); Assert.AreEqual(2, Recues(DEMANDE_MOREE), "la maison publiée");
            Vector3 siege = carte.PositionSurLaCarte(new PointCarte(s.x, s.y), ReperesDeDepart.HAUTEUR_LIEU).Value; Vector3 cam = objet.transform.InverseTransformPoint(carte.camera.transform.position);
            Assert.IsTrue(carte.Vue.Echelle < 1f && carte.Vue.Centre == new Vector2(siege.x, siege.z) && carte.Vue.Demi >= VueDeCarte.DEMI_MIN_KM && Mathf.Abs(cam.x - siege.x) < 0.01f && Mathf.Abs(cam.z - siege.z) < 0.01f && Mathf.Abs(carte.camera.orthographicSize - carte.Vue.Demi) < 0.01f, carte.Vue.Centre + " demi " + carte.Vue.Demi + " caméra " + cam);
            foreach (var p in Quatre()) { Transform lieu = LieuPose(p.rang); Vector3 attendu = carte.PositionSurLaCarte(new PointCarte(p.x, p.y), ReperesDeDepart.HAUTEUR_LIEU).Value; Vector3 vue = lieu != null ? carte.camera.WorldToViewportPoint(lieu.position) : Vector3.zero; Assert.IsTrue(lieu != null && Egal(lieu.localPosition, attendu) && lieu.Find("Disque").gameObject.activeInHierarchy && vue.x >= 0f && vue.x <= 1f && vue.y >= 0f && vue.y <= 1f, "rang " + p.rang + " " + vue); }
            Assert.IsNull(LieuPose(4), "le voisin a un disque");
            StringAssert.Contains(s.maison, reperes.TexteAffiche); StringAssert.Contains(s.siege, reperes.TexteAffiche); StringAssert.Contains("\nLieux servis : 4", reperes.TexteAffiche);
            Assert.IsTrue(reperes.RecuDuChoix.Acceptee && reperes.ChoixAffiche == null && reperes.FicheAffichee == null, reperes.ChoixAffiche);
        }
        [Test] public void Trois_lieux_tenus_posent_trois_disques() {
            Publier(MAISON_MOREE); ServirLieu(CorpsLieu(AvecVoisin()));
            string trois = maisons[DEMANDE_MOREE].corps.Replace(",{\"cell_id\":10340,\"rang\":3}", ""); Assert.AreNotEqual(maisons[DEMANDE_MOREE].corps, trois); maisons[DEMANDE_MOREE] = (200, trois);
            Monter(); Jusqua(1, () => DisquesActifs() == 3 && DepartsActifs() == 0);
            Assert.IsTrue(LieuPose(0) != null && LieuPose(1) != null && LieuPose(2) != null && LieuPose(3) == null, "quatre disques figés");
        }
        [TestCase("404", "statut 404")] [TestCase("siege", "siège sans cellule sur la carte servie")] [TestCase("point", "point nul")]
        [TestCase("rang", "rang 3 absent")] [TestCase("maitre", "maître contradictoire")] [TestCase("vide", "aucun lieu tenu")]
        public void Une_absence_de_domaine_nomme_sa_cause_puis_reprend(string cas, string attendu) {
            const string raison = "siège sans cellule sur la carte servie"; string vraie = maisons[DEMANDE_MOREE].corps; var pts = AvecVoisin();
            if (cas == "point") pts[3] = (3L, double.NaN, 0d, MAISON_MOREE);
            if (cas == "rang") pts = pts.Where(p => p.rang != 3).ToArray();
            if (cas == "maitre") pts[3] = (pts[3].rang, pts[3].x, pts[3].y, "seigneurie-9");
            Publier(null); ServirLieu(CorpsLieu(pts)); Monter();
            Jusqua(1, () => reperes.ReperesPoses == 6 && fiche.MondeLu != null && fiche.MaisonDuJoueur == null);
            if (cas == "404") maisons[DEMANDE_MOREE] = (404, "{\"erreur\":\"maison inconnue\"}");
            if (cas == "siege") maisons[DEMANDE_MOREE] = (200, "{\"id\":\"seigneurie-3\",\"nom\":\"Paléologue\",\"siege\":{\"cell_id\":null,\"rang\":null,\"nom\":\"Mistra\",\"point\":null},\"lieux\":[],\"absents\":{\"siege\":\"" + raison + "\"}}");
            if (cas == "vide") maisons[DEMANDE_MOREE] = (200, vraie.Replace("\"lieux\":[{\"cell_id\":10340,\"rang\":0},{\"cell_id\":10340,\"rang\":1},{\"cell_id\":10340,\"rang\":2},{\"cell_id\":10340,\"rang\":3}]", "\"lieux\":[]"));
            Vector2 centre = carte.Vue.Centre; float echelle = carte.Vue.Echelle, taille = carte.camera.orthographicSize; Publier(MAISON_MOREE);
            Jusqua(2, () => reperes.TexteAffiche != null && DisquesActifs() == 0 && DepartsActifs() == 6 && carte.Vue.Echelle == echelle && carte.Vue.Centre == centre);
            StringAssert.Contains(attendu, reperes.TexteAffiche); Assert.AreEqual(taille, carte.camera.orthographicSize);
            maisons[DEMANDE_MOREE] = (200, vraie); ServirLieu(CorpsLieu(AvecVoisin()));
            Jusqua(2 + ReperesDeDepart.PERIODE_RELECTURE_S, () => DisquesActifs() == 4 && DepartsActifs() == 0);
            StringAssert.DoesNotContain(attendu, reperes.TexteAffiche); StringAssert.Contains("Mistra", reperes.TexteAffiche); StringAssert.Contains("\nLieux servis : 4", reperes.TexteAffiche);
        }
        [Test] public void Le_domaine_rendu_garde_la_vue_que_le_joueur_glisse() {
            Publier(null); ServirLieu(CorpsLieu(AvecVoisin())); Monter();
            Jusqua(1, () => reperes.ReperesPoses == 6 && fiche.MondeLu != null);
            MeshRenderer[] cellules = objet.transform.Find("Cellules de la carte").GetComponentsInChildren<MeshRenderer>();
            var avant = cellules.Select(m => (m, m.sharedMaterial, m.sharedMaterial.color)).ToArray(); Publier(MAISON_MOREE);
            Jusqua(2, () => DisquesActifs() == 4 && DepartsActifs() == 0);
            foreach (var (m, mat, col) in avant) Assert.IsTrue(m.sharedMaterial == mat && m.sharedMaterial.color == col, m.name);
            Material joueur = null;
            for (long r = 0; r < 4; r++) { Transform lieu = LieuPose(r); var disque = lieu.Find("Disque").GetComponent<MeshRenderer>(); var bord = lieu.Find("Bord").GetComponent<MeshRenderer>(); if (joueur == null) joueur = disque.sharedMaterial; Assert.IsTrue(disque.sharedMaterial == joueur && ((Color32)disque.sharedMaterial.color).Equals((Color32)ReperesDeDepart.COULEUR_JOUEUR) && bord.sharedMaterial.color.maxColorComponent < 0.25f && bord.gameObject.activeInHierarchy && disque.GetComponent<Collider>() == null, "rang " + r); }
            CelluleDeCarte sous = carte.CelluleSous(LieuPose(0).position);
            Assert.AreNotEqual((Color32)cellules.Single(m => m.name == "Cellule " + sous.CellId).sharedMaterial.color, (Color32)joueur.color);
            int depots = Recues("/intention"); reperes.Survoler(Ecran(MOREE)); reperes.Choisir(Ecran(MOREE));
            Assert.IsTrue(reperes.Survolee == null && reperes.FicheAffichee == null && Recues("/intention") == depots, Recues("/intention") + " dépôts");
            Vector2 avantGlisse = carte.Vue.Centre; carte.Vue.Glisser(new Vector2(40f, -30f), 900f); Vector2 glisse = carte.Vue.Centre;
            Assert.AreNotEqual(avantGlisse, glisse); int n = DisquesActifs();
            for (int i = 0; i < 4; i++) { carte.Pas(5 + i); fiche.Pas(5 + i); reperes.Pas(5 + i); }
            Assert.AreEqual(glisse, carte.Vue.Centre); Assert.AreEqual(n, DisquesActifs());
        }
        // Bar manque : la maison publiée descend quand même, puis aucun `/departs` ne part ; une lecture en vol à la pose (posée ici, hors du faux service) ne repose rien.
        [Test] public void Une_maison_etrangere_absente_laisse_descendre_sans_relire_les_departs() {
            maisons["/maison?id=seigneurie-1"] = (404, "{\"erreur\":\"maison inconnue\"}"); Publier(null); ServirLieu(CorpsLieu(AvecVoisin())); Monter(); Lecture<DepartsLus> lus; using (var d = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) lus = d.Lire(); var tenue = Lecture<MaisonLue>.De(Maison(3)); lock (recues) recues.Clear();
            Jusqua(1, () => reperes.ReperesPoses == 5 && !reperes.LectureEnVol && fiche.MondeLu != null && fiche.MaisonDuJoueur == null);
            var vol = new System.Threading.Tasks.TaskCompletionSource<(Lecture<DepartsLus>, List<(FicheDeDepart, Lecture<MaisonLue>)>)>(); typeof(ReperesDeDepart).GetField("enCours", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).SetValue(reperes, vol.Task);
            reponses.Enqueue((200, "{\"acceptee\":true,\"appliquee_au_tick\":4}")); Cliquer(MOREE); Publier(MAISON_MOREE);
            Jusqua(2, () => DisquesActifs() == 4 && DepartsActifs() == 0 && carte.Vue.Echelle < 1f); Vector2 centre = carte.Vue.Centre; string texte = reperes.TexteAffiche;
            Assert.IsTrue(reperes.LectureEnVol && texte != null && texte.Contains("Mistra") && !texte.Contains(ReperesDeDepart.MESSAGE_ABSENCE), "« " + texte + " »"); vol.SetResult((lus, lus.Donnees.Fiches.Select(f => (f, tenue)).ToList()));
            for (int i = 1; i <= 4; i++) { double t = 2 + i * ReperesDeDepart.PERIODE_RELECTURE_S; carte.Pas(t); fiche.Pas(t); reperes.Pas(t); Thread.Sleep(50); reperes.Pas(t); } int n = Recues("/intention"); reperes.Survoler(Ecran(MOREE)); reperes.Choisir(Ecran(MOREE));
            Assert.IsTrue(Recues("/departs") == 1 && Recues("/maison?id=seigneurie-1") == 1 && !reperes.LectureEnVol && reperes.ReperesPoses == 5 && DepartsActifs() == 0 && DisquesActifs() == 4 && reperes.Survolee == null && n == Recues("/intention") && carte.Vue.Centre == centre && carte.Vue.Echelle < 1f && reperes.TexteAffiche == texte, Recues("/departs") + " /departs, " + reperes.ReperesPoses + " repères ; « " + reperes.TexteAffiche + " »");
        }
        // Lot #729 — la maison publiée nomme son siège sur la carte, du nom que `/maison` sert, juste au nord de son disque ; rien avant.
        private TextMesh NomDuSiege() => objet.transform.Find(ReperesDeDepart.RACINE_LIEUX + "/" + ReperesDeDepart.NOM_DU_SIEGE)?.GetComponent<TextMesh>();
        [TestCase("Mistra")] [TestCase("Mistra servie au test")]
        public void La_maison_publiee_nomme_son_siege_du_nom_servi(string servi) {
            var s = SIEGES[2]; maisons[DEMANDE_MOREE] = (200, maisons[DEMANDE_MOREE].corps.Replace("\"nom\":\"Mistra\"", "\"nom\":\"" + servi + "\"")); Publier(null); ServirLieu(CorpsLieu(AvecVoisin())); Monter();
            Jusqua(1, () => reperes.ReperesPoses == 6 && fiche.MondeLu != null && fiche.MaisonDuJoueur == null); Assert.IsNull(NomDuSiege(), "un siège nommé avant la maison publiée");
            Publier(MAISON_MOREE); Jusqua(2, () => DisquesActifs() == 4 && DepartsActifs() == 0); TextMesh nom = NomDuSiege();
            Vector3 siege = carte.PositionSurLaCarte(new PointCarte(s.x, s.y), CarteDessinee.HAUTEUR_NOM).Value + new Vector3(0, 0, ReperesDeDepart.DIAMETRE_BORD_KM / 2); Vector3 vue = nom != null ? carte.camera.WorldToViewportPoint(nom.transform.position) : Vector3.zero;
            Assert.IsTrue(nom != null && nom.text == servi && nom.gameObject.activeInHierarchy && nom.color == Color.black && nom.anchor == TextAnchor.MiddleCenter && Egal(nom.transform.localPosition, siege) && vue.x > 0f && vue.x < 1f && vue.y > 0f && vue.y < 1f, "nom « " + nom?.text + " » en " + nom?.transform.localPosition.ToString("R") + ", vu en " + vue);
            Assert.AreEqual(1, objet.GetComponentsInChildren<TextMesh>(true).Count(t => t.text == servi), "le siège n'a pas un seul nom");
        }
    }
}
