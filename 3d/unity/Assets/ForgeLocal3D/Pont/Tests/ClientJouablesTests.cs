using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;
namespace Forge.Pont.Tests
{
    // Un faux service rend la réponse figée de /jouables (graine 0, tick 0) ; le client la relit exactement, ou nomme la clé fautive.
    public sealed class ClientJouablesTests
    {
        static readonly object Absent = new object();
        const string SceneDeBiskra = "Forge_Desert_Ville_ksar_des_sept_puits";
        int port; HttpListener ecoute; Thread fil; readonly List<string> recues = new List<string>();
        [SetUp] public void PortLibre() { var sonde = new TcpListener(IPAddress.Loopback, 0); sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop(); lock (recues) recues.Clear(); }
        [TearDown] public void Fermer() { ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }
        void Servir(string corps, int statut = 200)
        {
            byte[] octets = Encoding.UTF8.GetBytes(corps); var auditeur = ecoute = new HttpListener(); auditeur.Prefixes.Add("http://127.0.0.1:" + port + "/"); auditeur.Start();
            (fil = new Thread(() => { try { while (true) { var c = auditeur.GetContext(); var m = new MemoryStream(); c.Request.InputStream.CopyTo(m); lock (recues) recues.Add(c.Request.HttpMethod + " " + c.Request.Url.PathAndQuery + " [" + Encoding.UTF8.GetString(m.ToArray()) + "]"); c.Response.StatusCode = statut; c.Response.ContentLength64 = octets.Length; c.Response.OutputStream.Write(octets, 0, octets.Length); c.Response.OutputStream.Close(); } } catch (Exception) { } }) { IsBackground = true }).Start();
        }
        static string texteFige;
        static string Texte() => texteFige ?? (texteFige = Encoding.UTF8.GetString(File.ReadAllBytes(Path.Combine(Application.dataPath, "ForgeLocal3D/Pont/Tests/jouables-graine0-tick0.json"))));
        string[] Recues() { lock (recues) return recues.ToArray(); }
        Lecture<JouablesLus> Lire(string corps, int statut = 200) { Servir(corps, statut); using (var client = new ClientJouables(port, ClientJouables.DelaiMinimal)) return client.Lire(); }
        static void Absente(Lecture<JouablesLus> lecture, params string[] attendus)
        { Assert.IsTrue(!lecture.Presente && lecture.Donnees == null, lecture.Absence); StringAssert.StartsWith("jouables : ", lecture.Absence); string detail = lecture.Absence.Substring("jouables : ".Length); foreach (string attendu in attendus) StringAssert.Contains(attendu, detail); }
        static int FinChaine(string t, int i) { for (i++; t[i] != '"'; i++) if (t[i] == '\\') i++; return i + 1; }
        static int FinValeur(string t, int i) { if (t[i] == '"') return FinChaine(t, i); if (t[i] != '{' && t[i] != '[') { int j = i; while (",}]".IndexOf(t[j]) < 0) j++; return j; } int p = 0; do { if (t[i] == '"') i = FinChaine(t, i); else { if (t[i] == '{' || t[i] == '[') p++; else if (t[i] == '}' || t[i] == ']') p--; i++; } } while (p > 0); return i; }
        static int Chercher(string t, int i, string cle, out int debut) { debut = -1; for (i++; t[i] != '}'; ) { int o = i, a = FinChaine(t, i), v = a + 1; if (t.Substring(o + 1, a - o - 2) == cle) { debut = o; return v; } i = FinValeur(t, v); if (t[i] == ',') i++; } return -1; }
        static void Localiser(string t, string chemin, out int cle, out int debut, out int fin) { int i = 0; cle = 0; foreach (string morceau in chemin.Split('.')) { int c = morceau.IndexOf('['); i = Chercher(t, i, c < 0 ? morceau : morceau.Substring(0, c), out cle); Assert.GreaterOrEqual(i, 0, chemin); if (c >= 0) { Assert.AreEqual('[', t[i]); i++; for (int n = 0, k = int.Parse(morceau.Substring(c + 1, morceau.Length - c - 2), CultureInfo.InvariantCulture); n < k; n++) { i = FinValeur(t, i); Assert.AreEqual(',', t[i]); i++; } } } debut = i; fin = FinValeur(t, i); }
        static string Image(object v) => v == Absent ? "absent" : v == null ? "null" : v is string s ? "t:" + s : v is double d ? d.ToString("R", CultureInfo.InvariantCulture) : v is bool b ? (b ? "true" : "false") : v is List<object> l ? "L" + l.Count : v is Dictionary<string, object> o ? "O" + o.Count : "?";
        static object Aller(object cur, string chemin) { foreach (string morceau in chemin.Split('.')) { int c = morceau.IndexOf('['); var objet = cur as Dictionary<string, object>; if (objet == null || !objet.TryGetValue(c < 0 ? morceau : morceau.Substring(0, c), out cur)) return Absent; if (c >= 0) cur = ((List<object>)cur)[int.Parse(morceau.Substring(c + 1, morceau.Length - c - 2), CultureInfo.InvariantCulture)]; } return cur; }
        // `nouveau` nul retire la clé. Le témoin au chemin change, et le JSON reste valide.
        static string Muter(string t, string chemin, string nouveau) { Localiser(t, chemin, out int cle, out int debut, out int fin); int a = debut, b = fin; if (nouveau == null) { a = cle; if (a > 0 && t[a - 1] == ',') a--; else if (b < t.Length && t[b] == ',') b++; } string mute = t.Substring(0, a) + (nouveau ?? "") + t.Substring(b); Assert.AreNotEqual(Image(Aller(LecteurJson.LireObjet(t), chemin)), Image(Aller(LecteurJson.LireObjet(mute), chemin)), chemin); return mute; }
        static long N(object v) => (long)(double)v;
        static string T(object v) => (string)v;
        static void MemeIdentite(IdentiteDePays lue, object json, string ou)
        { var o = (Dictionary<string, object>)json; Assert.IsTrue(lue != null && lue.Id == T(o["id"]) && lue.Nom == T(o["nom"]), ou); }
        static void Egales(JouablesLus lus, string texte)
        {
            var racine = LecteurJson.LireObjet(texte); var date = (Dictionary<string, object>)racine["date"]; var fiches = (List<object>)racine["jouables"];
            Assert.IsTrue(lus.Tick == N(racine["tick"]) && lus.Date.Annee == N(date["annee"]) && lus.Date.JourDeLAnnee == N(date["jour_de_l_annee"]) && lus.Fiches.Count == fiches.Count);
            for (int i = 0; i < fiches.Count; i++)
            {
                var j = (Dictionary<string, object>)fiches[i]; FicheJouable f = lus.Fiches[i]; string ou = "jouables[" + i + "]";
                Assert.IsTrue(f.Id == T(j["id"]) && f.Nom == T(j["nom"]) && f.Sorte == T(j["sorte"]) && f.Lieux == N(j["lieux"]), ou);
                MemeIdentite(f.Pays, j["pays"], ou + ".pays");
                var regne = (List<object>)j["regne"]; Assert.AreEqual(regne.Count, f.Regne.Count, ou + ".regne"); for (int r = 0; r < regne.Count; r++) MemeIdentite(f.Regne[r], regne[r], ou + ".regne[" + r + "]");
                var s = (Dictionary<string, object>)j["siege"]; Assert.IsTrue(f.Siege.Nom == T(s["nom"]) && f.Siege.Lieu == T(s["lieu"]) && f.Siege.CellId == (s["cell_id"] == null ? (long?)null : N(s["cell_id"])), ou + ".siege");
                if (j["suzerain"] == null) Assert.IsNull(f.Suzerain, ou + ".suzerain");
                else { var z = (Dictionary<string, object>)j["suzerain"]; Assert.IsTrue(f.Suzerain != null && f.Suzerain.Id == T(z["id"]) && f.Suzerain.Nom == T(z["nom"]), ou + ".suzerain"); MemeIdentite(f.Suzerain.Pays, z["pays"], ou + ".suzerain.pays"); }
                var v = (Dictionary<string, object>)j["ville"]; Assert.IsTrue(f.Ville.Batie == (bool)v["batie"] && f.Ville.Scene == T(v["scene"]) && f.Ville.Raison == T(v["raison"]), ou + ".ville");
            }
        }
        static FicheJouable Fiche(JouablesLus lus, string id) => lus.Fiches.Single(f => f.Id == id);

        [Test] public void LaReponseFigeeSeRelitExactement()
        {
            string texte = Texte(); Lecture<JouablesLus> lecture = Lire(texte); JouablesLus lus = lecture.Donnees;
            CollectionAssert.AreEqual(new[] { "GET /jouables []" }, Recues());
            Assert.IsTrue(lecture.Presente && lecture.Absence == null, lecture.Absence);
            Egales(lus, texte);
            Assert.IsTrue(lus.Tick == 0 && lus.Date.Annee == 1400 && lus.Date.JourDeLAnnee == 1 && lus.Fiches.Count == 2236);
            CollectionAssert.AreEqual(new[] { "seigneurie-1", "seigneurie-2", "seigneurie-3", "seigneurie-4", "seigneurie-5", "seigneurie-6" }, lus.Fiches.Take(6).Select(f => f.Id).ToArray());
            FicheJouable bar = lus.Fiches[0];
            Assert.IsTrue(bar.Nom == "Bar" && bar.Sorte == "seigneurie" && bar.Lieux == 4 && bar.Pays.Id == "seigneurie-1" && bar.Pays.Nom == "Duché de Bar" && bar.Regne.Count == 1 && bar.Regne[0].Id == "seigneurie-1");
            Assert.IsTrue(bar.Siege.Nom == "Bar-le-Duc" && bar.Siege.Lieu == "Bar-le-Duc" && bar.Siege.CellId == 10430);
            Assert.IsTrue(bar.Suzerain.Id == "grande-3" && bar.Suzerain.Nom == "Valois" && bar.Suzerain.Pays.Id == "puissance-3" && bar.Suzerain.Pays.Nom == "France");
            Assert.IsTrue(lus.Fiches.Any(f => f.Suzerain == null) && lus.Fiches.Any(f => f.Regne.Count > 1));
            Assert.Throws<NotSupportedException>(() => ((IList<FicheJouable>)lus.Fiches).Add(null)); Assert.Throws<NotSupportedException>(() => ((IList<IdentiteDePays>)bar.Regne).Add(null));
        }
        [Test] public void BiskraEstBatieEtNommeSaScene()
        {
            FicheJouable zab = Fiche(Lire(Texte()).Donnees, "seigneurie-6");
            Assert.IsTrue(zab.Ville.Batie && zab.Ville.Raison == null && zab.Ville.Scene.EndsWith(SceneDeBiskra + ".unity"), zab.Ville.Scene);
            Assert.AreEqual(SceneDeBiskra, zab.Ville.NomDeScene);
            Assert.IsTrue(zab.Pays.Nom == "Émirat du Zab" && zab.Siege.Lieu == "Biskra" && zab.Siege.CellId == 10103 && zab.Suzerain.Pays.Id == "puissance-35");
        }
        [Test] public void LaMaisonDeFranceNEstPasBatieEtDitPourquoi()
        {
            JouablesLus lus = Lire(Texte()).Donnees; FicheJouable valois = Fiche(lus, "grande-3");
            Assert.IsTrue(valois.Nom == "Valois" && valois.Pays.Nom == "France" && !valois.Ville.Batie && valois.Ville.Scene == null && valois.Ville.NomDeScene == null && !string.IsNullOrWhiteSpace(valois.Ville.Raison), valois.Ville.Raison);
            Assert.AreEqual(1, lus.Fiches.Count(f => f.Ville.Batie));
        }
        [Test] public void LeNomDeSceneEstLeFichierSansDossierNiExtension()
        {
            Assert.AreEqual("A_b", new VilleJouable(true, "3d/unity/Assets/Scenes/A_b.unity", null).NomDeScene);
            Assert.AreEqual("A_b", new VilleJouable(true, "3d\\unity\\Scenes\\A_b.unity", null).NomDeScene);
            Assert.AreEqual("A_b", new VilleJouable(true, "A_b", null).NomDeScene);
            Assert.IsNull(new VilleJouable(false, null, "pas bâtie").NomDeScene);
        }
        [Test] public void UnNomUnLieuUneCelluleEtUnSuzerainNulsSontDesMesures()
        {
            string texte = Texte(); foreach (string chemin in new[] { "jouables[0].nom", "jouables[0].pays.nom", "jouables[0].siege.nom", "jouables[0].siege.lieu", "jouables[0].siege.cell_id", "jouables[0].suzerain", "jouables[0].regne[0].nom" }) texte = Muter(texte, chemin, "null");
            Lecture<JouablesLus> lecture = Lire(texte); Assert.IsTrue(lecture.Presente, lecture.Absence); Egales(lecture.Donnees, texte);
            FicheJouable f = lecture.Donnees.Fiches[0];
            Assert.IsTrue(f.Nom == null && f.Pays.Nom == null && f.Regne[0].Nom == null && f.Siege.Nom == null && f.Siege.Lieu == null && f.Siege.CellId == null && f.Suzerain == null);
        }
        [Test] public void UnNomDeSuzerainEtLeNomDeSonPaysNulsSontDesMesures()
        {
            string texte = Muter(Muter(Texte(), "jouables[0].suzerain.nom", "null"), "jouables[0].suzerain.pays.nom", "null");
            Lecture<JouablesLus> lecture = Lire(texte); Assert.IsTrue(lecture.Presente, lecture.Absence); Egales(lecture.Donnees, texte);
            Assert.IsTrue(lecture.Donnees.Fiches[0].Suzerain.Nom == null && lecture.Donnees.Fiches[0].Suzerain.Pays.Nom == null);
        }
        [Test] public void UneCleAbsenteRefuseTouteLaReponse([Values("tick", "date", "jouables", "jouables[0].id", "jouables[0].nom", "jouables[0].sorte", "jouables[0].lieux", "jouables[0].pays", "jouables[0].regne", "jouables[0].siege", "jouables[0].suzerain", "jouables[0].ville",
            "jouables[0].pays.id", "jouables[0].pays.nom", "jouables[0].regne[0].id", "jouables[0].regne[0].nom", "jouables[0].siege.nom", "jouables[0].siege.lieu", "jouables[0].siege.cell_id", "jouables[0].suzerain.id", "jouables[0].suzerain.nom", "jouables[0].suzerain.pays", "jouables[0].suzerain.pays.id",
            "jouables[0].ville.batie", "jouables[0].ville.scene", "jouables[0].ville.raison", "jouables[5].ville.scene", "jouables[5].ville.raison")] string chemin)
            => Absente(Lire(Muter(Texte(), chemin, null)), chemin, "clé absente");
        [Test] public void UneValeurFautiveRefuseTouteLaReponse([Values("jouables|[]|tableau non vide", "jouables|null|tableau non vide", "jouables[1].id|\"seigneurie-1\"|déjà lu", "jouables[0].id|\" \"|texte non vide", "jouables[0].id|1|texte non vide",
            "jouables[0].nom|\" \"|texte non vide ou null", "jouables[0].nom|3|texte non vide ou null", "jouables[0].sorte|null|texte non vide", "jouables[0].lieux|\"4\"|entier", "jouables[0].lieux|-1|entier", "jouables[0].lieux|1.5|entier", "jouables[0].lieux|true|entier",
            "jouables[0].pays|null|objet", "jouables[0].pays.id|7|texte non vide", "jouables[0].pays.nom|\"\"|texte non vide ou null", "jouables[0].regne|null|tableau", "jouables[0].regne[0]|null|objet", "jouables[0].siege|[]|objet",
            "jouables[0].siege.cell_id|-1|entier", "jouables[0].siege.cell_id|\"10430\"|entier", "jouables[0].siege.cell_id|true|entier", "jouables[0].siege.lieu|4|texte non vide ou null", "jouables[0].suzerain|25|null ou un objet", "jouables[0].suzerain.id|1|texte non vide", "jouables[0].suzerain.pays|null|objet",
            "jouables[0].ville|null|objet", "jouables[0].ville.batie|0|booléen", "jouables[5].ville.batie|\"true\"|booléen", "jouables[0].ville.batie|null|booléen", "jouables[0].ville.scene|3|texte non vide ou null", "jouables[0].ville.raison|false|texte non vide ou null", "date.jour_de_l_annee|0|entier", "tick|-1|entier")] string cas)
        { string[] m = cas.Split('|'); Absente(Lire(Muter(Texte(), m[0], m[1])), m[0], m[2]); }
        [Test] public void UneVilleIncoherenteRefuseTouteLaReponse([Values(
            "jouables[5].ville.scene|null|jouables[5].ville.scene", "jouables[5].ville.scene|\" \"|jouables[5].ville.scene", "jouables[5].ville.raison|\"pas bâtie\"|jouables[5].ville.raison",
            "jouables[0].ville.raison|null|jouables[0].ville.raison", "jouables[0].ville.raison|\" \"|jouables[0].ville.raison", "jouables[0].ville.batie|true|jouables[0].ville")] string cas)
        { string[] m = cas.Split('|'); Absente(Lire(Muter(Texte(), m[0], m[1])), m[2]); }
        [Test] public void UnJsonCoupeEstRefuse()
        { string texte = Texte(), coupe = texte.Substring(0, texte.Length - 1); Assert.AreNotEqual(texte, coupe); Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(coupe)); Absente(Lire(coupe), "JSON invalide"); }
        [Test] public void UnDelaiOuUnPortIlliciteNePartPas()
        {
            Servir("{}"); Assert.IsTrue(ClientJouables.DelaiMinimal == TimeSpan.FromSeconds(10));
            foreach (TimeSpan delai in new[] { TimeSpan.FromSeconds(2), Timeout.InfiniteTimeSpan, TimeSpan.FromMilliseconds((double)int.MaxValue + 1) })
                Assert.Throws<ArgumentOutOfRangeException>(() => new ClientJouables(port, delai));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientJouables(0, ClientJouables.DelaiMinimal));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientJouables(65536, ClientJouables.DelaiMinimal));
            Assert.AreEqual(0, Recues().Length);
            new ClientJouables(1, ClientJouables.DelaiMinimal).Dispose(); new ClientJouables(65535, ClientJouables.DelaiMinimal).Dispose();
        }
        [Test] public void UnStatutOuUnServiceAbsentNeProduitAucuneFiche([Values("404", "500", "absent")] string panne)
        {
            Lecture<JouablesLus> lecture;
            if (panne == "absent") using (var client = new ClientJouables(port, ClientJouables.DelaiMinimal)) lecture = client.Lire();
            else lecture = Lire("{\"erreur\":\"panne\"}", int.Parse(panne, CultureInfo.InvariantCulture));
            if (panne == "absent") Absente(lecture, "service absent"); else Absente(lecture, "statut " + panne, "{\"erreur\":\"panne\"}");
            if (panne == "404") StringAssert.StartsWith("jouables : statut 404", lecture.Absence);
        }
    }
}
