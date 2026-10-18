using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace Forge.Pont.Tests
{
    // Lot #679 — le pont lit /monde puis, pour une terre qui a un kit, /maison?id= : il dit où mener le joueur, ou pourquoi il ne le sait pas.
    public sealed class CapitaleDuJoueurTests
    {
        const string SceneDuKsar = "Forge_Desert_Ville_ksar_des_sept_puits";
        int port; HttpListener ecoute; Thread fil; readonly List<string> recues = new List<string>();
        [SetUp] public void PortLibre() { var s = new TcpListener(IPAddress.Loopback, 0); s.Start(); port = ((IPEndPoint)s.LocalEndpoint).Port; s.Stop(); lock (recues) recues.Clear(); }
        [TearDown] public void Fermer() { ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }
        // Le faux service répond selon le chemin : /monde d'un côté, /maison?id= de l'autre, quel que soit l'identifiant demandé.
        void Servir((int statut, string corps) monde, (int statut, string corps) maison)
        {
            var a = ecoute = new HttpListener(); a.Prefixes.Add("http://127.0.0.1:" + port + "/"); a.Start();
            (fil = new Thread(() => { try { while (true) { var c = a.GetContext(); string url = c.Request.RawUrl; lock (recues) recues.Add(c.Request.HttpMethod + " " + url);
                (int st, string tx) = url.StartsWith("/maison?id=", StringComparison.Ordinal) ? maison : url == "/monde" ? monde : (404, "{}"); c.Response.StatusCode = st; c.Response.Close(Encoding.UTF8.GetBytes(tx), true); } } catch (Exception) { } }) { IsBackground = true }).Start();
        }
        string[] Recues() { lock (recues) return recues.ToArray(); }
        // Un monde minimal valide : une cellule, qui n'est ni le siège du Zab ni celui de Bar.
        static string Monde(string maison) => "{\"tick\":0,\"date\":{\"annee\":1400,\"jour_de_l_annee\":1},\"cell_count\":1,\"cells\":[{\"cell_id\":7,\"population\":1,\"hunger_ticks\":0,\"food_deficit_kg\":0}]" + (maison == null ? "" : ",\"maison_du_joueur\":\"" + maison + "\"") + "}";
        static string Fige(string terre) => Encoding.UTF8.GetString(File.ReadAllBytes(Path.Combine(Application.dataPath, "ForgeLocal3D/Pont/Tests/maison-" + terre + "-graine0-tick0.json")));
        static string Zab => Fige("zab"); static string Bar => Fige("bar"); static string Id(string fiche) => (string)LecteurJson.LireObjet(fiche)["id"];
        static string Remplacer(string texte, string ancien, string nouveau)
        { int i = texte.IndexOf(ancien, StringComparison.Ordinal); Assert.IsTrue(i >= 0 && texte.LastIndexOf(ancien, StringComparison.Ordinal) == i, ancien); return texte.Substring(0, i) + nouveau + texte.Substring(i + ancien.Length); }
        Lecture<CapitaleAOuvrir> Lire(string maisonDuJoueur, (int, string) maison) { Servir((200, Monde(maisonDuJoueur)), maison); return AiguillageDeCapitale.Lire(port, TimeSpan.FromSeconds(5)); }
        static CapitaleAOuvrir Presente(Lecture<CapitaleAOuvrir> l) { Assert.IsTrue(l.Presente && l.Absence == null, l.Absence); return l.Donnees; }
        static void Absente(Lecture<CapitaleAOuvrir> l, string prefixe, string attendu)
        { Assert.IsTrue(!l.Presente && l.Donnees == null && !string.IsNullOrEmpty(l.Absence), "une destination de remplacement : " + l.Donnees?.Destination); StringAssert.StartsWith(prefixe, l.Absence); StringAssert.Contains(attendu, l.Absence); }
        [Test] public void LaTableNeConnaitQueLeZabEtSaSceneEstAuBuild()
        {
            string zab = Id(Zab), bar = Id(Bar);
            Assert.AreEqual(1, TerresAvecKit.Scenes.Count);
            Assert.AreEqual(zab, TerresAvecKit.Scenes.Keys.Single());
            Assert.IsFalse(TerresAvecKit.Scenes.ContainsKey(bar), bar);
            string scene = TerresAvecKit.Scenes[zab], projet = Path.GetDirectoryName(Application.dataPath);
            Assert.IsTrue(EditorBuildSettings.scenes.Any(s => s.enabled && Path.GetFileNameWithoutExtension(s.path) == scene && File.Exists(Path.Combine(projet, s.path))), scene);
            Assert.Throws<NotSupportedException>(() => ((IDictionary<string, string>)TerresAvecKit.Scenes).Add(bar, scene));
        }
        [Test] public void SansMaisonLeJoueurVaAuDepartSansLireDeFiche()
        {
            var c = Presente(Lire(null, (200, Zab)));
            Assert.IsTrue(c.Destination == DestinationDeCapitale.Depart && c.Maison == null && c.Scene == null && c.Cellule == null, c.Destination.ToString());
            CollectionAssert.AreEqual(new[] { "GET /monde" }, Recues());
            Assert.IsTrue(typeof(CapitaleAOuvrir).GetProperties().All(p => !p.CanWrite));
        }
        [Test] public void LeZabOuvreLeKsarASonSiege()
        {
            string zab = Id(Zab); var c = Presente(Lire(zab, (200, Zab)));
            Assert.IsTrue(c.Destination == DestinationDeCapitale.Ville && c.Maison == zab && c.Scene == SceneDuKsar && c.Cellule == 10103, c.Destination + " " + c.Cellule);
            CollectionAssert.AreEqual(new[] { "GET /monde", "GET /maison?id=" + zab }, Recues());
        }
        [Test] public void LaCelluleVientDuSiegeServi()
        {
            string deplace = Remplacer(Zab, "\"siege\":{\"cell_id\":10103", "\"siege\":{\"cell_id\":10104");
            StringAssert.Contains("{\"cell_id\":10103,\"rang\":0}", deplace);
            var c = Presente(Lire(Id(Zab), (200, deplace)));
            Assert.IsTrue(c.Destination == DestinationDeCapitale.Ville && c.Cellule == 10104, c.Destination + " " + c.Cellule);
        }
        [Test] public void BarNAPasEncoreDeKit()
        {
            string bar = Id(Bar); var c = Presente(Lire(bar, (200, Bar)));
            Assert.IsTrue(c.Destination == DestinationDeCapitale.PasDeKit && c.Maison == bar && c.Scene == null && c.Cellule == null, c.Destination.ToString());
            CollectionAssert.AreEqual(new[] { "GET /monde" }, Recues());
        }
        [Test] public void UneMaisonInconnueNAPasDeKit()
        { var c = Presente(Lire("seigneurie-99", (200, Zab))); Assert.IsTrue(c.Destination == DestinationDeCapitale.PasDeKit && c.Maison == "seigneurie-99" && c.Cellule == null, c.Destination.ToString()); }
        [Test] public void UnServiceAbsentNeMeneNullePart() => Absente(AiguillageDeCapitale.Lire(port, TimeSpan.FromSeconds(5)), "monde : ", "monde : service absent");
        [Test] public void UnMondeEnPanneNeMeneNullePart() { Servir((500, "{\"erreur\":\"casse\"}"), (200, Zab)); Absente(AiguillageDeCapitale.Lire(port, TimeSpan.FromSeconds(5)), "monde : ", "monde : statut 500"); }
        [Test] public void UneFicheEnPanneNeMeneNullePart() => Absente(Lire(Id(Zab), (500, "{\"erreur\":\"casse\"}")), "maison : ", "maison : statut 500");
        [Test] public void UneFicheDUneAutreMaisonEstRefusee() => Absente(Lire(Id(Zab), (200, Bar)), "maison : ", "maison : clé id");
        [Test] public void UnSiegeHorsCarteNOuvrePasDeVille()
        {
            string hors = Remplacer(Remplacer(Zab, "\"absents\":{}", "\"absents\":{\"siege\":\"hors_carte\"}"), "\"siege\":{\"cell_id\":10103,\"nom\":\"Biskra\",\"point\":{\"latitude\":34.85,\"longitude\":5.73,\"x_m\":3926430.32,\"y_m\":1322273.47},\"rang\":0}", "\"siege\":{\"cell_id\":null,\"nom\":\"Biskra\",\"point\":null,\"rang\":null}");
            Absente(Lire(Id(Zab), (200, hors)), "maison : ", "hors_carte");
        }
        [Test] public void UnAppelIlliciteNePartPas()
        {
            Servir((200, Monde(Id(Zab))), (200, Zab));
            foreach (int hors in new[] { 0, -1, 65536 }) Assert.Throws<ArgumentOutOfRangeException>(() => AiguillageDeCapitale.Lire(hors, TimeSpan.FromSeconds(1)));
            foreach (TimeSpan d in new[] { TimeSpan.Zero, TimeSpan.FromTicks(-1), Timeout.InfiniteTimeSpan, TimeSpan.FromMilliseconds((double)int.MaxValue + 1) })
                Assert.Throws<ArgumentOutOfRangeException>(() => AiguillageDeCapitale.Lire(port, d));
            Assert.AreEqual(0, Recues().Length);
        }
        // Lot #687 — la ville sait sur quelle cellule s'ouvrir : -forgeCarte, puis -forgeCell, puis l'éditeur, enfin l'aiguillage.
        int appels;
        Func<Lecture<CapitaleAOuvrir>> Compteur() { appels = 0; return () => { appels++; return AiguillageDeCapitale.Lire(port, TimeSpan.FromSeconds(5)); }; }
        // Le service sert le Zab : une décision prise sur les arguments ou l'éditeur ne doit rien lui demander.
        Lecture<OuvertureDecidee> SansRequete(string ligne, bool editeur)
        {
            Servir((200, Monde(Id(Zab))), (200, Zab));
            var d = OuvertureDeLaCapitale.Decider(ligne.Split(' '), editeur, Compteur());
            Assert.AreEqual(0, appels, ligne); CollectionAssert.IsEmpty(Recues(), ligne); Assert.IsNotNull(d, ligne); return d;
        }
        static void OuverteEnVille(Lecture<OuvertureDecidee> d, long cellule)
        {
            Assert.IsTrue(d.Presente && d.Absence == null, d.Absence);
            Assert.IsTrue(d.Donnees.Mode == ModeDOuverture.Ville && d.Donnees.Cellule == cellule && d.Donnees.Scene == null, d.Donnees.Mode + " " + d.Donnees.Cellule + " " + d.Donnees.Scene);
        }
        static void SansOuverture(Lecture<OuvertureDecidee> d, string prefixe, string attendu)
        { Assert.IsTrue(!d.Presente && d.Donnees == null && !string.IsNullOrEmpty(d.Absence), "une ouverture de remplacement : " + d.Donnees?.Mode + " " + d.Donnees?.Cellule); StringAssert.StartsWith(prefixe, d.Absence); StringAssert.Contains(attendu, d.Absence); }
        [TestCase("Forge.exe -forgeCell 42", false, 42L)]
        [TestCase("Forge.exe -forgeCell 42", true, 42L)]
        [TestCase("Forge.exe", true, 1175L)]
        public void LesArgumentsEtLEditeurOuvrentLaVilleSansRequete(string ligne, bool editeur, long cellule)
        {
            OuverteEnVille(SansRequete(ligne, editeur), cellule);
            Assert.IsTrue(typeof(OuvertureDecidee).GetProperties().All(p => !p.CanWrite));
        }
        [TestCase("Forge.exe -forgeCell")]
        [TestCase("Forge.exe -forgeCell abc")]
        [TestCase("Forge.exe -forgeCell -3")]
        public void UneCelluleFautiveResteUneAbsenceSansRequete(string ligne)
        {
            string[] arguments = ligne.Split(' ');
            PanneauLieu.LireCellule(arguments, PanneauLieu.CELLULE_PAR_DEFAUT, out string attendue);
            Assert.IsFalse(string.IsNullOrEmpty(attendue), ligne);
            var d = SansRequete(ligne, false);
            SansOuverture(d, PanneauLieu.ARGUMENT_CELLULE, attendue);
            Assert.AreEqual(attendue, d.Absence);
            if (arguments.Length == 3) StringAssert.Contains("« " + arguments[2] + " »", d.Absence);
        }
        [TestCase("Forge.exe -forgeCell 1175 -forgeCarte", false)]
        [TestCase("Forge.exe -forgeCarte -forgeCell abc", true)]
        public void LaCarteDemandeePasseAvantLaCellule(string ligne, bool editeur)
        {
            var d = SansRequete(ligne, editeur);
            Assert.IsTrue(d.Presente && d.Absence == null, d.Absence);
            Assert.IsTrue(d.Donnees.Mode == ModeDOuverture.LaisseeALaCarte && d.Donnees.Cellule == null && d.Donnees.Scene == null, d.Donnees.Mode + " " + d.Donnees.Cellule);
        }
        [Test] public void SansArgumentsNiAiguillageRienNePart()
        {
            Servir((200, Monde(Id(Zab))), (200, Zab));
            var compteur = Compteur();
            Assert.Throws<ArgumentNullException>(() => OuvertureDeLaCapitale.Decider(null, false, compteur));
            Assert.Throws<ArgumentNullException>(() => OuvertureDeLaCapitale.Decider(null, true, compteur));
            Assert.Throws<ArgumentNullException>(() => OuvertureDeLaCapitale.Decider(new[] { "Forge.exe" }, false, null));
            Assert.AreEqual(0, appels); CollectionAssert.IsEmpty(Recues());
        }
        // Le jeu bâti, sans argument : la décision suit l'aiguillage, branché sur le faux service.
        static Lecture<OuvertureDecidee> Batie(Func<Lecture<CapitaleAOuvrir>> aiguillage) => OuvertureDeLaCapitale.Decider(new[] { "Forge.exe" }, false, aiguillage);
        Lecture<OuvertureDecidee> BatieServie(string maisonDuJoueur, (int, string) maison)
        { Servir((200, Monde(maisonDuJoueur)), maison); var d = Batie(Compteur()); Assert.AreEqual(1, appels); return d; }
        static void ALaCarte(Lecture<OuvertureDecidee> d)
        {
            Assert.IsTrue(d.Presente && d.Absence == null, d.Absence);
            Assert.IsTrue(d.Donnees.Mode == ModeDOuverture.Carte && d.Donnees.Scene == OuvertureDeLaCarte.SCENE && d.Donnees.Cellule == null, d.Donnees.Mode + " " + d.Donnees.Cellule + " " + d.Donnees.Scene);
        }
        [Test] public void LeJeuBatiOuvreLeZabASonSiege()
        {
            string zab = Id(Zab); OuverteEnVille(BatieServie(zab, (200, Zab)), 10103);
            CollectionAssert.AreEqual(new[] { "GET /monde", "GET /maison?id=" + zab }, Recues());
        }
        [Test] public void LeJeuBatiSuitLeSiegeServi() => OuverteEnVille(BatieServie(Id(Zab), (200, Remplacer(Zab, "\"siege\":{\"cell_id\":10103", "\"siege\":{\"cell_id\":10104"))), 10104);
        [Test] public void LeJeuBatiEnvoieBarALaCarte() { ALaCarte(BatieServie(Id(Bar), (200, Bar))); CollectionAssert.AreEqual(new[] { "GET /monde" }, Recues()); }
        [Test] public void LeJeuBatiSansMaisonVaALaCarte() { ALaCarte(BatieServie(null, (200, Zab))); CollectionAssert.AreEqual(new[] { "GET /monde" }, Recues()); }
        [Test] public void LeJeuBatiSansServiceNOuvreRien() { var d = Batie(Compteur()); Assert.AreEqual(1, appels); SansOuverture(d, "monde : ", "monde : service absent"); }
        [Test] public void LeJeuBatiAvecUneFicheEnPanneNOuvreRien() => SansOuverture(BatieServie(Id(Zab), (500, "{\"erreur\":\"casse\"}")), "maison : ", "maison : statut 500");
        [Test] public void LAbsenceDeLAiguillagePasseMotPourMot()
        {
            int vus = 0;
            var d = Batie(() => { vus++; return Lecture<CapitaleAOuvrir>.Absent("cause témoin 687"); });
            Assert.AreEqual(1, vus); SansOuverture(d, "cause témoin 687", "cause témoin 687"); Assert.AreEqual("cause témoin 687", d.Absence);
            Assert.Throws<InvalidOperationException>(() => Batie(() => null));
        }
        // Lot #701 — la cellule remise par le passage de la carte passe avant -forgeCarte, -forgeCell et l'éditeur, sans requête.
        Lecture<OuvertureDecidee> RemiseSansRequete(string ligne, bool editeur, long? remise)
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty);
            Servir((200, Monde(Id(Zab))), (200, Zab));
            var d = OuvertureDeLaCapitale.Decider(ligne.Split(' '), editeur, remise, Compteur());
            Assert.AreEqual(0, appels, ligne); CollectionAssert.IsEmpty(Recues(), ligne); Assert.IsNotNull(d, ligne); return d;
        }
        [TestCase("Forge.exe", true)]
        [TestCase("Forge.exe -forgeCell 42", false)]
        [TestCase("Forge.exe -forgeCarte", false)]
        public void LaRemisePasseAvantTout(string ligne, bool editeur) => OuverteEnVille(RemiseSansRequete(ligne, editeur, 10104), 10104);
        [Test] public void SansRemiseLEditeurGardeLeKsar()
        {
            OuverteEnVille(RemiseSansRequete("Forge.exe", true, null), 1175);
            OuverteEnVille(OuvertureDeLaCapitale.Decider(new[] { "Forge.exe" }, true, Compteur()), 1175);
            Assert.AreEqual(0, appels); CollectionAssert.IsEmpty(Recues());
        }
        [Test] public void UneRemiseNegativeEstRefuseeSansRequete()
        {
            PassageALaCapitale.PrendreCelluleRemise(string.Empty);
            Servir((200, Monde(Id(Zab))), (200, Zab)); var compteur = Compteur();
            Assert.Throws<ArgumentOutOfRangeException>(() => OuvertureDeLaCapitale.Decider(new[] { "Forge.exe" }, false, -1, compteur));
            Assert.AreEqual(0, appels); CollectionAssert.IsEmpty(Recues());
        }
    }
}
