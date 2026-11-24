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
    public sealed class ClientLieuxTests
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
        static string Texte() => Encoding.UTF8.GetString(File.ReadAllBytes(Path.Combine(Application.dataPath, "ForgeLocal3D/Pont/Tests/" + EuropeDeTest.LIEUX)));
        string[] Recues() { lock (recues) return recues.ToArray(); }
        Lecture<LieuxLus> Lire(string corps) { Servir(corps); using (var client = new ClientLieux(port, ClientLieux.DelaiMinimal)) return client.Lire(); }
        static void Absente(Lecture<LieuxLus> lecture, params string[] attendus)
        { Assert.IsTrue(!lecture.Presente && lecture.Donnees == null, lecture.Absence); StringAssert.StartsWith("lieux : ", lecture.Absence); string detail = lecture.Absence.Substring("lieux : ".Length); foreach (string attendu in attendus) StringAssert.Contains(attendu, detail); }
        static int FinChaine(string t, int i) { for (i++; t[i] != '"'; i++) if (t[i] == '\\') i++; return i + 1; }
        static int FinValeur(string t, int i) { if (t[i] == '"') return FinChaine(t, i); if (t[i] != '{' && t[i] != '[') { int j = i; while (",}]".IndexOf(t[j]) < 0) j++; return j; } int p = 0; do { if (t[i] == '"') i = FinChaine(t, i); else { if (t[i] == '{' || t[i] == '[') p++; else if (t[i] == '}' || t[i] == ']') p--; i++; } } while (p > 0); return i; }
        static int Chercher(string t, int i, string cle, out int debut) { debut = -1; for (i++; t[i] != '}'; ) { int o = i, a = FinChaine(t, i), v = a + 1; if (t.Substring(o + 1, a - o - 2) == cle) { debut = o; return v; } i = FinValeur(t, v); if (t[i] == ',') i++; } return -1; }
        static void Localiser(string t, string chemin, out int cle, out int debut, out int fin) { int i = 0; cle = 0; foreach (string morceau in chemin.Split('.')) { int c = morceau.IndexOf('['); i = Chercher(t, i, c < 0 ? morceau : morceau.Substring(0, c), out cle); Assert.GreaterOrEqual(i, 0, chemin); if (c >= 0) { Assert.AreEqual('[', t[i]); i++; for (int n = 0, k = int.Parse(morceau.Substring(c + 1, morceau.Length - c - 2), CultureInfo.InvariantCulture); n < k; n++) { i = FinValeur(t, i); Assert.AreEqual(',', t[i]); i++; } } } debut = i; fin = FinValeur(t, i); }
        static string Image(object v) => v == Absent ? "absent" : v == null ? "null" : v is string s ? "t:" + s : v is double d ? d.ToString("R", CultureInfo.InvariantCulture) : v is bool b ? (b ? "true" : "false") : v is List<object> l ? "L" + l.Count : v is Dictionary<string, object> o ? "O" + o.Count : "?";
        static object Aller(object cur, string chemin) { foreach (string morceau in chemin.Split('.')) { int c = morceau.IndexOf('['); var objet = cur as Dictionary<string, object>; if (objet == null || !objet.TryGetValue(c < 0 ? morceau : morceau.Substring(0, c), out cur)) return Absent; if (c >= 0) cur = ((List<object>)cur)[int.Parse(morceau.Substring(c + 1, morceau.Length - c - 2), CultureInfo.InvariantCulture)]; } return cur; }
        // `nouveau` nul retire la clé. Le témoin au chemin change, et le JSON reste valide.
        static string Muter(string t, string chemin, string nouveau) { Localiser(t, chemin, out int cle, out int debut, out int fin); int a = debut, b = fin; if (nouveau == null) { a = cle; if (a > 0 && t[a - 1] == ',') a--; else if (b < t.Length && t[b] == ',') b++; } string mute = t.Substring(0, a) + (nouveau ?? "") + t.Substring(b); Assert.AreNotEqual(Image(Aller(LecteurJson.LireObjet(t), chemin)), Image(Aller(LecteurJson.LireObjet(mute), chemin)), chemin); return mute; }
        static long N(object v) => (long)(double)v;
        // Les valeurs lues égalent, au chiffre près, celles que `LecteurJson` lit du même texte. Un `null` JSON est une réserve absente.
        static int Egales(LieuxLus lus, string texte)
        {
            var racine = LecteurJson.LireObjet(texte); var date = (Dictionary<string, object>)racine["date"]; var cellules = (List<object>)racine["cells"];
            Assert.Greater(cellules.Count, 0, "un échantillon vide ne prouve rien");
            Assert.IsTrue(lus.Tick == N(racine["tick"]) && lus.Date.Annee == N(date["annee"]) && lus.Date.JourDeLAnnee == N(date["jour_de_l_annee"]) && lus.CellCount == N(racine["cell_count"]) && lus.Cellules.Count == cellules.Count);
            int lieux = 0;
            for (int i = 0; i < cellules.Count; i++)
            {
                var j = (Dictionary<string, object>)cellules[i]; CelluleServie c = lus.Cellules[i]; var ls = (List<object>)j["lieux"];
                Assert.IsTrue(c.CellId == N(j["cell_id"]) && c.Lieux.Count == ls.Count && ReferenceEquals(lus.Cellule(c.CellId), c), "cellule " + i);
                for (int k = 0; k < ls.Count; k++)
                {
                    var jl = (Dictionary<string, object>)ls[k]; LieuServi l = c.Lieux[k]; string ici = "cellule " + i + ", lieu " + k;
                    Assert.IsTrue(l.Rang == N(jl["rang"]) && l.Population == N(jl["population"]) && l.SurfaceKm2 == (double)jl["surface_km2"], ici);
                    if (jl["reserve_jours"] == null) Assert.IsNull(l.ReserveJours, ici); else Assert.AreEqual((double)jl["reserve_jours"], l.ReserveJours, ici);
                    lieux++;
                }
            }
            return lieux;
        }
        [Test] public void LesCellulesEtLeursLieuxSontRelusExactement()
        {
            string texte = Texte(); Lecture<LieuxLus> lecture = Lire(texte); LieuxLus lus = lecture.Donnees;
            CollectionAssert.AreEqual(new[] { "GET /lieux []" }, Recues());
            Assert.IsTrue(lecture.Presente && lecture.Absence == null, lecture.Absence);
            int lieux = Egales(lus, texte);
            Assert.IsTrue(lus.Tick == 3 && lus.Date.Annee == 1400 && lus.Date.JourDeLAnnee == 4 && lus.CellCount == 596 && lus.Cellules.Count == 596);
            Assert.AreEqual(6619, lieux); int somme = 0; var reserves = 0;
            foreach (CelluleServie c in lus.Cellules) { somme += c.Lieux.Count; foreach (LieuServi l in c.Lieux) if (l.ReserveJours.HasValue && l.ReserveJours.Value != 0) reserves++; }
            Assert.AreEqual(6619, somme); Assert.Greater(reserves, 0, "au moins une réserve non nulle");
            CelluleServie premiere = lus.Cellules[0]; LieuServi p = premiere.Lieux[0];
            Assert.IsTrue(premiere.CellId == 1175 && premiere.Lieux.Count == 1 && p.Rang == 0 && p.Population == 327 && p.SurfaceKm2 == 42.491425 && p.ReserveJours == 0.0);
            Assert.IsTrue(lus.Cellules[85].Lieux.Count == 3 && lus.Cellules[85].Lieux[2].Rang == 2);
            Assert.Throws<NotSupportedException>(() => ((IList<CelluleServie>)lus.Cellules).Add(null)); Assert.Throws<NotSupportedException>(() => ((IList<LieuServi>)premiere.Lieux).Add(null));
        }
        [Test] public void UneCelluleSeRetrouveParSonIdentifiantEtUneInconnueRendNull()
        {
            LieuxLus lus = Lire(Texte()).Donnees;
            foreach (CelluleServie c in lus.Cellules) Assert.IsTrue(ReferenceEquals(lus.Cellule(c.CellId), c), "cellule " + c.CellId);
            Assert.IsTrue(lus.Cellule(1175).Lieux.Count == 1 && lus.Cellule(1176).Lieux[0].Population == 911);
            foreach (long inconnue in new[] { -1L, 0L, 1174L, 99999999L }) Assert.IsNull(lus.Cellule(inconnue), "cellule " + inconnue);
        }
        [Test] public void UneReserveNulleSeLitNullEtUneDetteSeLitTelle()
        {
            string texte = Muter(Muter(Muter(Texte(), "cells[0].lieux[0].reserve_jours", "null"), "cells[0].lieux[0].population", "0"), "cells[3].lieux[0].reserve_jours", "-12.5");
            Lecture<LieuxLus> lecture = Lire(texte); Assert.IsTrue(lecture.Presente, lecture.Absence); Egales(lecture.Donnees, texte);
            LieuServi vide = lecture.Donnees.Cellules[0].Lieux[0], dette = lecture.Donnees.Cellules[3].Lieux[0];
            Assert.IsTrue(vide.Population == 0 && !vide.ReserveJours.HasValue, "un lieu sans habitants a une réserve absente, pas zéro");
            Assert.IsTrue(dette.ReserveJours.HasValue && dette.ReserveJours.Value == -12.5);
        }
        [Test] public void UneCleAbsenteRefuseTouteLaReponse([Values("tick", "date", "cell_count", "cells", "cells[3].cell_id", "cells[3].lieux", "cells[3].lieux[0].population", "cells[3].lieux[0].rang", "cells[3].lieux[0].reserve_jours", "cells[3].lieux[0].surface_km2", "cells[85].lieux[2].surface_km2")] string chemin)
            => Absente(Lire(Muter(Texte(), chemin, null)), chemin, "clé absente");
        [Test] public void UneValeurFautiveRefuseTouteLaReponse([Values(
            "cells|[]|tableau non vide", "cells|null|tableau non vide", "cells|{\"a\":1}|tableau non vide", "cells[3]|null|objet", "cells[3]|7|objet",
            "cells[3].cell_id|-1|entier", "cells[3].cell_id|\"1181\"|entier", "cells[3].cell_id|1.5|entier", "cells[1].cell_id|1175|déjà lu",
            "cells[3].lieux|[]|tableau non vide", "cells[3].lieux|null|tableau non vide", "cells[3].lieux|{\"a\":1}|tableau non vide", "cells[3].lieux[0]|3|objet",
            "cells[3].lieux[0].population|-1|entier", "cells[3].lieux[0].population|1.5|entier", "cells[3].lieux[0].population|true|entier", "cells[3].lieux[0].population|\"12\"|entier", "cells[3].lieux[0].population|null|entier",
            "cells[3].lieux[0].surface_km2|0|> 0", "cells[3].lieux[0].surface_km2|-2.5|> 0", "cells[3].lieux[0].surface_km2|null|nombre", "cells[3].lieux[0].surface_km2|\"x\"|nombre", "cells[3].lieux[0].surface_km2|true|nombre",
            "cells[3].lieux[0].reserve_jours|\"x\"|null ou un nombre", "cells[3].lieux[0].reserve_jours|true|null ou un nombre", "cells[3].lieux[0].reserve_jours|{\"a\":1}|null ou un nombre", "cells[3].lieux[0].reserve_jours|[]|null ou un nombre",
            "cells[85].lieux[1].rang|0|déjà lu", "cells[85].lieux[2].rang|1|déjà lu", "cells[85].lieux[1].rang|5|rang 1", "cells[85].lieux[0].rang|1|rang 0", "cells[85].lieux[1].rang|1.5|entier", "cells[85].lieux[1].rang|\"1\"|entier", "cells[85].lieux[1].rang|-1|entier",
            "cell_count|595|596", "cell_count|597|596", "cell_count|\"596\"|entier", "cell_count|-1|entier", "cell_count|null|entier",
            "date.jour_de_l_annee|0|entier")] string cas)
        { string[] m = cas.Split('|'); Absente(Lire(Muter(Texte(), m[0], m[1])), m[0], m[2]); }
        [Test] public void UnJsonCoupeEstRefuse()
        { string texte = Texte(), coupe = texte.Substring(0, texte.Length - 1); Assert.AreNotEqual(texte, coupe); Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(coupe)); Absente(Lire(coupe), "JSON invalide"); }
        [Test] public void UnDelaiOuUnPortIlliciteNePartPas()
        {
            Servir("{}"); Assert.IsTrue(ClientLieux.DelaiMinimal == TimeSpan.FromSeconds(10));
            foreach (TimeSpan delai in new[] { TimeSpan.FromSeconds(2), Timeout.InfiniteTimeSpan, TimeSpan.FromMilliseconds((double)int.MaxValue + 1) })
                Assert.Throws<ArgumentOutOfRangeException>(() => new ClientLieux(port, delai));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientLieux(0, ClientLieux.DelaiMinimal));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientLieux(65536, ClientLieux.DelaiMinimal));
            Assert.AreEqual(0, Recues().Length);
            new ClientLieux(1, ClientLieux.DelaiMinimal).Dispose(); new ClientLieux(65535, ClientLieux.DelaiMinimal).Dispose();
        }
        [Test] public void UnServiceLentRestePresent()
        {
            Servir(Texte(), attenteMs: 2500);
            using (var client = new ClientLieux(port, ClientLieux.DelaiMinimal))
            { var lecture = client.Lire(); Assert.IsTrue(lecture.Presente && lecture.Donnees.Cellules.Count == 596 && lecture.Absence == null, lecture.Absence); }
        }
        [Test] public void UnServiceMuetAbsentOuEnPanneNeProduitAucuneCellule([Values("muet", "absent", "500")] string panne)
        {
            if (panne == "500") Servir("{\"erreur\":\"panne\"}", 500); else if (panne == "muet") Servir(Texte(), muet: true);
            var chrono = Stopwatch.StartNew(); Lecture<LieuxLus> lecture;
            using (var client = new ClientLieux(port, ClientLieux.DelaiMinimal)) lecture = client.Lire();
            if (panne == "muet") Assert.IsTrue(chrono.ElapsedMilliseconds >= 9900, "mesuré " + chrono.ElapsedMilliseconds);
            if (panne == "500") Absente(lecture, "500", "{\"erreur\":\"panne\"}"); else Absente(lecture, panne == "muet" ? "délai dépassé" : "service absent");
        }
    }
}
