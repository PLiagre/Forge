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
    }
}
