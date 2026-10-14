using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;
namespace Forge.Pont.Tests
{
    public sealed class ClientDepartsTests
    {
        static readonly object Absent = new object();
        int port; HttpListener ecoute; Thread fil; readonly List<string> recues = new List<string>();
        [SetUp] public void PortLibre() { var sonde = new TcpListener(IPAddress.Loopback, 0); sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop(); lock (recues) recues.Clear(); }
        [TearDown] public void Fermer() { ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }
        void Servir(string corps, int statut = 200, int attenteMs = 0, bool muet = false)
        {
            byte[] octets = Encoding.UTF8.GetBytes(corps); var auditeur = ecoute = new HttpListener(); auditeur.Prefixes.Add("http://127.0.0.1:" + port + "/"); auditeur.Start();
            (fil = new Thread(() => { try { while (true) { var c = auditeur.GetContext(); var m = new MemoryStream(); c.Request.InputStream.CopyTo(m); lock (recues) recues.Add(c.Request.HttpMethod + " " + c.Request.Url.PathAndQuery + " [" + Encoding.UTF8.GetString(m.ToArray()) + "]"); if (muet) continue; if (attenteMs > 0) Thread.Sleep(attenteMs); c.Response.StatusCode = statut; c.Response.ContentLength64 = octets.Length; c.Response.OutputStream.Write(octets, 0, octets.Length); c.Response.OutputStream.Close(); } } catch (Exception) { } }) { IsBackground = true }).Start();
        }
        static string Texte() => Encoding.UTF8.GetString(File.ReadAllBytes(Path.Combine(Application.dataPath, "ForgeLocal3D/Pont/Tests/departs-graine0-tick3.json")));
        string[] Recues() { lock (recues) return recues.ToArray(); }
        Lecture<DepartsLus> Lire(string corps) { Servir(corps); using (var client = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) return client.Lire(); }
        static void Absente(Lecture<DepartsLus> lecture, params string[] attendus)
        { Assert.IsTrue(!lecture.Presente && lecture.Donnees == null, lecture.Absence); StringAssert.StartsWith("departs : ", lecture.Absence); string detail = lecture.Absence.Substring("departs : ".Length); foreach (string attendu in attendus) StringAssert.Contains(attendu, detail); }
        static int FinChaine(string t, int i) { for (i++; t[i] != '"'; i++) if (t[i] == '\\') i++; return i + 1; }
        static int FinValeur(string t, int i) { if (t[i] == '"') return FinChaine(t, i); if (t[i] != '{' && t[i] != '[') { int j = i; while (",}]".IndexOf(t[j]) < 0) j++; return j; } int p = 0; do { if (t[i] == '"') i = FinChaine(t, i); else { if (t[i] == '{' || t[i] == '[') p++; else if (t[i] == '}' || t[i] == ']') p--; i++; } } while (p > 0); return i; }
        static int Chercher(string t, int i, string cle, out int debut) { debut = -1; for (i++; t[i] != '}'; ) { int o = i, a = FinChaine(t, i), v = a + 1; if (t.Substring(o + 1, a - o - 2) == cle) { debut = o; return v; } i = FinValeur(t, v); if (t[i] == ',') i++; } return -1; }
        static void Localiser(string t, string chemin, out int cle, out int debut, out int fin) { int i = 0; cle = 0; foreach (string morceau in chemin.Split('.')) { int c = morceau.IndexOf('['); i = Chercher(t, i, c < 0 ? morceau : morceau.Substring(0, c), out cle); Assert.GreaterOrEqual(i, 0, chemin); if (c >= 0) { Assert.AreEqual('[', t[i]); i++; for (int n = 0, k = int.Parse(morceau.Substring(c + 1, morceau.Length - c - 2), CultureInfo.InvariantCulture); n < k; n++) { i = FinValeur(t, i); Assert.AreEqual(',', t[i]); i++; } } } debut = i; fin = FinValeur(t, i); }
        static string Image(object v) => v == Absent ? "absent" : v == null ? "null" : v is string s ? "t:" + s : v is double d ? d.ToString("R", CultureInfo.InvariantCulture) : v is bool b ? (b ? "true" : "false") : v is List<object> l ? "L" + l.Count : v is Dictionary<string, object> o ? "O" + o.Count : "?";
        static object Aller(object cur, string chemin) { foreach (string morceau in chemin.Split('.')) { int c = morceau.IndexOf('['); var objet = cur as Dictionary<string, object>; if (objet == null || !objet.TryGetValue(c < 0 ? morceau : morceau.Substring(0, c), out cur)) return Absent; if (c >= 0) cur = ((List<object>)cur)[int.Parse(morceau.Substring(c + 1, morceau.Length - c - 2), CultureInfo.InvariantCulture)]; } return cur; }
        // `nouveau` nul retire la clé. Le témoin au chemin change, et le JSON reste valide.
        static string Muter(string t, string chemin, string nouveau) { Localiser(t, chemin, out int cle, out int debut, out int fin); int a = debut, b = fin; if (nouveau == null) { a = cle; if (a > 0 && t[a - 1] == ',') a--; else if (b < t.Length && t[b] == ',') b++; } string mute = t.Substring(0, a) + (nouveau ?? "") + t.Substring(b); Assert.AreNotEqual(Image(Aller(LecteurJson.LireObjet(t), chemin)), Image(Aller(LecteurJson.LireObjet(mute), chemin)), chemin); return mute; }
        static long N(object v) => (long)(double)v;
        static void Meme(IdentiteDeCarte lue, object json)
        {
            if (json == null) Assert.IsNull(lue);
            else { var o = (Dictionary<string, object>)json; Assert.IsTrue(lue != null && lue.Id == N(o["id"]) && lue.Nom == (string)o["nom"]); }
        }
        static void Egales(DepartsLus lus, string texte)
        {
            var racine = LecteurJson.LireObjet(texte); var date = (Dictionary<string, object>)racine["date"]; var fiches = (List<object>)racine["departs"];
            Assert.IsTrue(lus.Tick == N(racine["tick"]) && lus.Date.Annee == N(date["annee"]) && lus.Date.JourDeLAnnee == N(date["jour_de_l_annee"]) && lus.Fiches.Count == fiches.Count);
            for (int i = 0; i < fiches.Count; i++)
            {
                var j = (Dictionary<string, object>)fiches[i]; FicheDeDepart f = lus.Fiches[i]; var s = (Dictionary<string, object>)j["siege"]; var vs = (List<object>)j["voisins"];
                Assert.IsTrue(f.Id == N(j["id"]) && f.Nom == (string)j["nom"] && f.Maison == (string)j["maison"] && f.CellId == N(j["cell_id"]) && f.Habitants == N(j["habitants"]) && f.Siege.Nom == (string)s["nom"] && f.Siege.Lat == (double)s["lat"] && f.Siege.Lon == (double)s["lon"] && f.Voisins.Count == vs.Count, "fiche " + i);
                Meme(f.Suzerain, j["suzerain"]);
                for (int v = 0; v < vs.Count; v++) { var jv = (Dictionary<string, object>)vs[v]; Assert.IsTrue(f.Voisins[v].CellId == N(jv["cell_id"]) && f.Voisins[v].Habitants == N(jv["habitants"]), i + "." + v); Meme(f.Voisins[v].Puissance, jv["puissance"]); }
            }
        }
        [Test] public void LesFichesEtLeursVoisinsSontRelusExactement()
        {
            string texte = Texte(); Lecture<DepartsLus> lecture = Lire(texte); DepartsLus lus = lecture.Donnees;
            CollectionAssert.AreEqual(new[] { "GET /departs []" }, Recues());
            Assert.IsTrue(lecture.Presente && lecture.Absence == null, lecture.Absence);
            Egales(lus, texte);
            Assert.IsTrue(lus.Tick == 3 && lus.Date.Annee == 1400 && lus.Date.JourDeLAnnee == 4 && lus.Fiches.Count == 6);
            var ids = new long[6]; var cells = new long[6];
            for (int i = 0; i < 6; i++) { ids[i] = lus.Fiches[i].Id; cells[i] = lus.Fiches[i].CellId; }
            CollectionAssert.AreEqual(new[] { 1L, 2L, 3L, 4L, 5L, 6L }, ids); CollectionAssert.AreEqual(new[] { 10430L, 10465L, 10340L, 10334L, 10337L, 10103L }, cells);
            FicheDeDepart moree = lus.Fiches[2], zab = lus.Fiches[5];
            Assert.IsTrue(moree.Maison == "Paléologue" && moree.Habitants == 80919 && moree.Siege.Nom == "Mistra" && moree.Siege.Lat == 37.074 && moree.Siege.Lon == 22.367 && moree.Suzerain.Id == 25 && moree.Suzerain.Nom == "Byzance");
            Assert.IsTrue(zab.Maison == "Banou Mozni" && zab.Habitants == 3459 && zab.Siege.Nom == "Biskra" && zab.Siege.Lat == 34.85 && zab.Siege.Lon == 5.73 && zab.Suzerain.Id == 35 && zab.Suzerain.Nom == "Hafsides" && zab.Voisins[1].CellId == 10087 && zab.Voisins[1].Puissance == null);
            Assert.Throws<NotSupportedException>(() => ((IList<FicheDeDepart>)lus.Fiches).Add(null)); Assert.Throws<NotSupportedException>(() => ((IList<VoisinDeDepart>)moree.Voisins).Add(null));
        }
        [Test] public void LesChampsHorsLectureNeSontPasExiges()
        {
            string texte = Texte();
            foreach (string cle in "religion source production_kg_par_tick maison_du_suzerain cellules_du_suzerain habitants_du_suzerain".Split(' ')) texte = Muter(texte, "departs[2]." + cle, null);
            Lecture<DepartsLus> lecture = Lire(texte);
            Assert.IsTrue(lecture.Presente, lecture.Absence); Egales(lecture.Donnees, texte);
        }
        [Test] public void UnSuzerainNulDesVoisinsVidesEtZeroHabitantRestentLisibles()
        {
            string texte = Muter(Muter(Muter(Texte(), "departs[2].suzerain", "null"), "departs[2].voisins", "[]"), "departs[2].habitants", "0");
            Lecture<DepartsLus> lecture = Lire(texte); FicheDeDepart moree = lecture.Donnees.Fiches[2];
            Assert.IsTrue(lecture.Presente && lecture.Donnees.Fiches.Count == 6, lecture.Absence); Egales(lecture.Donnees, texte);
            Assert.IsTrue(moree.Suzerain == null && moree.Voisins.Count == 0 && moree.Habitants == 0);
        }
        [Test] public void UneCleAbsenteRefuseTouteLaReponse([Values("tick", "date", "departs", "departs[2].id", "departs[2].nom", "departs[2].maison", "departs[2].siege", "departs[2].cell_id", "departs[2].habitants", "departs[2].suzerain", "departs[2].voisins", "departs[2].siege.nom", "departs[2].suzerain.nom", "departs[2].voisins[0].cell_id", "departs[5].voisins[1].puissance")] string chemin)
            => Absente(Lire(Muter(Texte(), chemin, null)), chemin, "clé absente");
        [Test] public void UneValeurFautiveRefuseTouteLaReponse([Values("departs|[]|tableau non vide", "departs|null|tableau non vide", "departs[1].id|1|déjà lu", "departs[2].nom|\" \"|texte non vide", "departs[2].maison|{\"a\":1}|texte non vide", "departs[2].siege|null|objet", "departs[2].siege.lat|91|latitude", "departs[2].siege.lon|\"x\"|nombre", "departs[2].habitants|-1|entier", "departs[2].habitants|1.5|entier", "departs[2].habitants|true|entier", "departs[2].cell_id|-1|entier", "departs[2].suzerain|25|null ou un objet", "departs[2].suzerain.id|\"25\"|entier", "departs[2].voisins|null|tableau", "departs[2].voisins[0].habitants|-1|entier", "departs[2].voisins[0].puissance|\"x\"|null ou un objet", "date.jour_de_l_annee|0|entier")] string cas)
        { string[] m = cas.Split('|'); Absente(Lire(Muter(Texte(), m[0], m[1])), m[0], m[2]); }
        [Test] public void UnJsonCoupeEstRefuse()
        { string texte = Texte(), coupe = texte.Substring(0, texte.Length - 1); Assert.AreNotEqual(texte, coupe); Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(coupe)); Absente(Lire(coupe), "JSON invalide"); }
        [Test] public void UnDelaiOuUnPortIlliciteNePartPas()
        {
            Servir("{}"); Assert.IsTrue(ClientDeparts.DelaiMinimal == TimeSpan.FromSeconds(10));
            foreach (TimeSpan delai in new[] { TimeSpan.FromSeconds(2), Timeout.InfiniteTimeSpan, TimeSpan.FromMilliseconds((double)int.MaxValue + 1) })
                Assert.Throws<ArgumentOutOfRangeException>(() => new ClientDeparts(port, delai));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientDeparts(0, ClientDeparts.DelaiMinimal));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientDeparts(65536, ClientDeparts.DelaiMinimal));
            Assert.AreEqual(0, Recues().Length);
            new ClientDeparts(1, ClientDeparts.DelaiMinimal).Dispose(); new ClientDeparts(65535, ClientDeparts.DelaiMinimal).Dispose();
        }
        [Test] public void UnServiceLentRestePresent()
        {
            Servir(Texte(), attenteMs: 2500);
            using (var client = new ClientDeparts(port, ClientDeparts.DelaiMinimal))
            { var lecture = client.Lire(); Assert.IsTrue(lecture.Presente && lecture.Donnees.Fiches.Count == 6 && lecture.Absence == null, lecture.Absence); }
        }
        [Test] public void UnServiceMuetAbsentOuEnPanneNeProduitAucuneFiche([Values("muet", "absent", "500")] string panne)
        {
            if (panne == "500") Servir("{\"erreur\":\"panne\"}", 500); else if (panne == "muet") Servir(Texte(), muet: true);
            var chrono = Stopwatch.StartNew(); Lecture<DepartsLus> lecture;
            using (var client = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) lecture = client.Lire();
            if (panne == "muet") Assert.IsTrue(chrono.ElapsedMilliseconds >= 9900, "mesuré " + chrono.ElapsedMilliseconds);
            if (panne == "500") Absente(lecture, "500", "{\"erreur\":\"panne\"}"); else Absente(lecture, panne == "muet" ? "délai dépassé" : "service absent");
        }
    }
}
