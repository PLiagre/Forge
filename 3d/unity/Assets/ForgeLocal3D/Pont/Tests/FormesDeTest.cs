using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Les formes que les tests donnent au terrain. Des terres témoins : chaque cellule en un seul lieu, de son contour, ou
    // coupée en lieux par des droites. Les réponses figées de l'Ouest (`carte-graine0-ouest.json`,
    // `formes-graine0-ouest.json`, `terres-graine0-tick24.json`), relevées du vrai service sur la graine 0 et lues
    // par les vrais clients, une fois pour tous les cas. Celles des Détroits (`carte-graine0-detroits.json`,
    // `formes-graine0-detroits.json`) sont relevées du même service, graine 0, au tick 30, sans IA ; elles ne gardent
    // que la cellule du bourg de Constantinople, où des lieux de Byzance côtoient des lieux ottomans, et ses
    // voisines de Thrace et de Bithynie, toutes ottomanes. Leurs terres sont celles de l'Europe
    // (`EuropeDeTest.TerresEurope`). Publique : les tests de l'interface lisent les mêmes Détroits.
    public static class FormesDeTest {
        public const string CARTE = "carte-graine0-ouest.json", FORMES = "formes-graine0-ouest.json", TERRES = "terres-graine0-tick24.json";
        public const string CARTE_DETROITS = "carte-graine0-detroits.json", FORMES_DETROITS = "formes-graine0-detroits.json";
        // La cellule de Pampelune, à la Navarre, dont des lieux sont à la Castille ; celles de Gênes et de Florence.
        public const long PAMPELUNE = 10192, GENES = 10456, FLORENCE = 10260;
        // La cellule du bourg de Constantinople (Byzance, dont des lieux sont aux Ottomans) ; ses voisines de Thrace
        // (Édirne et deux autres) et de Bithynie, aux Ottomans.
        public const long CONSTANTINOPLE = 10374, EDIRNE = 10366, THRACE_NORD = 10370, THRACE_OUEST = 10361, BITHYNIE = 10032;
        private static CarteLue carte; private static FormesLues formes; private static TerresDeLaCarte terres; private static TerrainDeCarte terrain;
        private static CarteLue carteDetroits; private static FormesLues formesDetroits; private static TerrainDeCarte terrainDetroits;

        public static CarteLue CarteOuest { get { Lire(); return carte; } }
        public static FormesLues FormesOuest { get { Lire(); return formes; } }
        public static TerresDeLaCarte TerresOuest { get { Lire(); return terres; } }
        // Le terrain des réponses figées, levé une fois.
        public static TerrainDeCarte TerrainOuest { get { Lire(); return terrain ?? (terrain = TerrainDeCarte.Lever(carte, formes)); } }

        public static CarteLue CarteDetroits { get { LireDetroits(); return carteDetroits; } }
        public static FormesLues FormesDetroits { get { LireDetroits(); return formesDetroits; } }
        // Le terrain des Détroits, levé une fois.
        public static TerrainDeCarte TerrainDetroits { get { LireDetroits(); return terrainDetroits ?? (terrainDetroits = TerrainDeCarte.Lever(carteDetroits, formesDetroits)); } }

        // Chaque cellule en un seul lieu, de son contour servi.
        public static FormesLues UnLieuParCellule(CarteLue lue) =>
            new FormesLues(null, lue.Cellules.Select(c => new FormeDeCellule(c.CellId, c.Contour, new[] { new FormeDeLieu(0, c.Contour) })));
        public static TerrainDeCarte Lever(CarteLue lue) => TerrainDeCarte.Lever(lue, UnLieuParCellule(lue));
        // Le corps de `/formes` qui répond à ce corps de `/carte` : chaque cellule en un seul lieu, de son contour servi.
        public static byte[] UnLieuParCelluleServi(byte[] carte) {
            var racine = LecteurJson.LireObjet(Encoding.UTF8.GetString(carte)); var s = new StringBuilder("{\"crs\":\"EPSG:3035\",\"version\":null,\"cells\":[");
            bool premiere = true;
            foreach (Dictionary<string, object> cellule in (List<object>)racine["cells"]) {
                if (!premiere) s.Append(','); premiere = false;
                string contour = Json(cellule["contour"]);
                s.Append("{\"cell_id\":").Append(Json(cellule["cell_id"])).Append(",\"contour\":").Append(contour).Append(",\"lieux\":[{\"rang\":0,\"contour\":").Append(contour).Append("}]}");
            }
            return Encoding.UTF8.GetBytes(s.Append("]}").ToString());
        }
        // Une valeur lue par LecteurJson, récrite en JSON.
        private static string Json(object valeur) {
            switch (valeur) {
                case null: return "null";
                case string texte: return "\"" + texte.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
                case double nombre: return nombre.ToString("R", CultureInfo.InvariantCulture);
                case bool oui: return oui ? "true" : "false";
                case List<object> liste: return "[" + string.Join(",", liste.Select(Json)) + "]";
                case Dictionary<string, object> objet: return "{" + string.Join(",", objet.Select(p => Json(p.Key) + ":" + Json(p.Value))) + "}";
                default: throw new ArgumentException("valeur JSON inconnue : " + valeur.GetType().Name);
            }
        }

        // Le pays de chaque lieu du terrain selon `/terres` : un indice par pays servi, 0 pour un lieu sans pays.
        public static int[] PaysDesLieux(TerrainDeCarte t, CarteLue lue, TerresDeLaCarte servies) {
            var indices = new Dictionary<string, int>(); var pays = new int[t.NombreDeLieux];
            for (int l = 0; l < pays.Length; l++) {
                string id = servies.PaysDuLieu(lue.Cellules[t.CelluleDuLieu(l)].CellId, t.RangDuLieu(l));
                if (id == null) continue;
                if (!indices.TryGetValue(id, out int k)) { k = indices.Count + 1; indices[id] = k; }
                pays[l] = k;
            }
            return pays;
        }

        // Les trois réponses figées, servies par un faux service et lues par ClientCarte, ClientFormes et ClientGuerre.
        private static void Lire() {
            if (carte != null) return;
            string dossier = Application.dataPath + "/ForgeLocal3D/Pont/Tests/";
            var corps = new Dictionary<string, byte[]> {
                { "/carte", File.ReadAllBytes(dossier + CARTE) }, { "/formes", File.ReadAllBytes(dossier + FORMES) }, { "/terres", File.ReadAllBytes(dossier + TERRES) }
            };
            try { Servir(corps, out carte, out formes, out terres); } catch { carte = null; throw; }
        }

        // Les deux réponses figées des Détroits, servies et lues de même.
        private static void LireDetroits() {
            if (carteDetroits != null) return;
            string dossier = Application.dataPath + "/ForgeLocal3D/Pont/Tests/";
            var corps = new Dictionary<string, byte[]> {
                { "/carte", File.ReadAllBytes(dossier + CARTE_DETROITS) }, { "/formes", File.ReadAllBytes(dossier + FORMES_DETROITS) }
            };
            try { Servir(corps, out carteDetroits, out formesDetroits, out _); } catch { carteDetroits = null; throw; }
        }

        // Sert ces corps par un faux service et les fait lire par les vrais clients ; `/terres` n'est lu que s'il est servi.
        private static void Servir(Dictionary<string, byte[]> corps, out CarteLue lueCarte, out FormesLues lueFormes, out TerresDeLaCarte lueTerres) {
            lueCarte = null; lueFormes = null; lueTerres = null;
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
                using (var c = new ClientCarte(port, ClientCarte.DelaiMinimal)) { LectureCarte l = c.Lire(); Assert.IsTrue(l.Presente, l.Absence); lueCarte = l.Carte; }
                using (var c = new ClientFormes(port, ClientFormes.DelaiMinimal)) { LectureFormes l = c.Lire(); Assert.IsTrue(l.Presente, l.Absence); lueFormes = l.Formes; }
                if (corps.ContainsKey("/terres"))
                    using (var c = new ClientGuerre(port, TimeSpan.FromSeconds(10))) { Lecture<TerresDeLaCarte> l = c.LireTerres(); Assert.IsTrue(l.Presente, l.Absence); lueTerres = l.Donnees; }
            } finally { ecoute.Close(); fil.Join(TimeSpan.FromSeconds(5)); }
        }
    }
}
