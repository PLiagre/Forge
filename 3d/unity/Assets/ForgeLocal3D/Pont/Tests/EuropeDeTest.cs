using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // La carte de toute l'Europe que les tests lisent. Les réponses figées (`carte-graine0-europe.json`, `terres-graine0-europe.json`,
    // `atlas-graine0.json`, `jouables-graine0-europe.json`) viennent du vrai service, graine 0, au tick 30, sans IA : elles sont
    // servies une fois par un faux service et lues par les vrais clients, `ClientCarte`, `ClientGuerre`, `ClientAtlas` et `ClientJouables`.
    // Le corps de `/atlas` est aussi gardé tel que `LecteurJson` le lit, pour juger ce que le client en a lu. `/formes` n'est pas relevé : le terrain prend
    // un lieu par cellule (`FormesDeTest.Lever`).
    internal static class EuropeDeTest {
        public const string CARTE = "carte-graine0-europe.json", TERRES = "terres-graine0-europe.json", ATLAS = "atlas-graine0.json", JOUABLES = "jouables-graine0-europe.json";
        private static CarteLue carte; private static TerresDeLaCarte terres; private static JouablesLus jouables; private static AtlasLu atlasLu; private static Dictionary<string, object> atlas; private static TerrainDeCarte terrain;

        public static CarteLue CarteEurope { get { Lire(); return carte; } }
        public static TerresDeLaCarte TerresEurope { get { Lire(); return terres; } }
        public static JouablesLus JouablesEurope { get { Lire(); return jouables; } }
        // L'atlas que `ClientAtlas` lit du corps servi.
        public static AtlasLu AtlasEurope { get { Lire(); return atlasLu; } }
        // L'objet que `LecteurJson` lit du corps brut de `/atlas`.
        public static Dictionary<string, object> AtlasBrut { get { Lire(); return atlas; } }
        // Le terrain des réponses figées, levé une fois : un lieu par cellule.
        public static TerrainDeCarte TerrainEurope { get { Lire(); return terrain ?? (terrain = FormesDeTest.Lever(carte)); } }

        // Le corps figé d'un fichier du dossier des tests.
        public static string Corps(string fichier) => Encoding.UTF8.GetString(File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/" + fichier));

        // Les quatre réponses figées, servies par un faux service et lues par les clients.
        private static void Lire() {
            if (carte != null) return;
            string dossier = Application.dataPath + "/ForgeLocal3D/Pont/Tests/";
            var corps = new Dictionary<string, byte[]> {
                { "/carte", File.ReadAllBytes(dossier + CARTE) }, { "/terres", File.ReadAllBytes(dossier + TERRES) },
                { "/atlas", File.ReadAllBytes(dossier + ATLAS) }, { "/jouables", File.ReadAllBytes(dossier + JOUABLES) }
            };
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start(); int port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop();
            var ecoute = new HttpListener(); ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/"); ecoute.Start();
            var fil = new Thread(() => {
                try {
                    while (true) {
                        HttpListenerContext ctx = ecoute.GetContext();
                        byte[] octets = corps.TryGetValue(ctx.Request.Url.AbsolutePath, out byte[] servis) ? servis : new byte[0];
                        ctx.Response.StatusCode = servis != null ? 200 : 404; ctx.Response.ContentLength64 = octets.Length;
                        ctx.Response.OutputStream.Write(octets, 0, octets.Length); ctx.Response.Close();
                    }
                } catch (Exception) { }
            }) { IsBackground = true };
            fil.Start();
            try {
                using (var c = new ClientCarte(port, ClientCarte.DelaiMinimal)) { LectureCarte l = c.Lire(); Assert.IsTrue(l.Presente, l.Absence); carte = l.Carte; }
                using (var c = new ClientGuerre(port, TimeSpan.FromSeconds(10))) { Lecture<TerresDeLaCarte> l = c.LireTerres(); Assert.IsTrue(l.Presente, l.Absence); terres = l.Donnees; }
                using (var c = new ClientAtlas(port, TimeSpan.FromSeconds(10))) { Lecture<AtlasLu> l = c.Lire(); Assert.IsTrue(l.Presente, l.Absence); atlasLu = l.Donnees; }
                using (var c = new ClientJouables(port, ClientJouables.DelaiMinimal)) { Lecture<JouablesLus> l = c.Lire(); Assert.IsTrue(l.Presente, l.Absence); jouables = l.Donnees; }
                atlas = LecteurJson.LireObjet(Encoding.UTF8.GetString(corps["/atlas"]));
            } catch { carte = null; throw; }
            finally { ecoute.Close(); fil.Join(TimeSpan.FromSeconds(5)); }
        }
    }
}
