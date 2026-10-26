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
    // Lot #186 — un faux service local rend un statut et des octets fixés ;
    // le client en relit les vrais chiffres, ou rend une absence qui nomme sa cause.
    public sealed class ClientLieuTests
    {
        private const long CellFigee = 9922;
        private static readonly TimeSpan Delai = TimeSpan.FromSeconds(5);

        private int port;
        private HttpListener ecoute;
        private Thread fil;

        [SetUp]
        public void PortLibre()
        {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start();
            port = ((IPEndPoint)sonde.LocalEndpoint).Port;
            sonde.Stop();
        }

        [TearDown]
        public void Fermer()
        {
            if (ecoute != null)
            {
                ecoute.Close();
                ecoute = null;
            }
            fil?.Join(TimeSpan.FromSeconds(5));
            fil = null;
        }

        // `redirection` : `/lieu` répond 302 vers ce chemin, qui rend `statut` et `corps`.
        // `muet` : la requête est acceptée et jamais répondue (le délai doit dépasser).
        private void Servir(int statut, string corps, string redirection = null, bool muet = false)
        {
            byte[] octets = Encoding.UTF8.GetBytes(corps);
            ecoute = new HttpListener();
            ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/");
            ecoute.Start();
            var auditeur = ecoute;
            fil = new Thread(() =>
            {
                while (true)
                {
                    HttpListenerContext contexte;
                    try { contexte = auditeur.GetContext(); }
                    catch (Exception) { return; }
                    if (muet) continue;
                    if (redirection != null && contexte.Request.Url.AbsolutePath == "/lieu")
                    {
                        contexte.Response.StatusCode = 302;
                        contexte.Response.RedirectLocation = "http://127.0.0.1:" + port + redirection;
                        contexte.Response.ContentLength64 = 0;
                        contexte.Response.OutputStream.Close();
                        continue;
                    }
                    contexte.Response.StatusCode = statut;
                    contexte.Response.ContentType = "application/json; charset=utf-8";
                    contexte.Response.ContentLength64 = octets.Length;
                    contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                    contexte.Response.OutputStream.Close();
                }
            }) { IsBackground = true };
            fil.Start();
        }

        private static string TexteFige(string nom)
        {
            string chemin = Path.Combine(Application.dataPath, "ForgeLocal3D/Pont/Tests/" + nom);
            Assert.IsTrue(File.Exists(chemin), "réponse figée absente : " + chemin);
            string texte = File.ReadAllText(chemin);
            Assert.IsNotEmpty(texte, "réponse figée vide : " + chemin);
            return texte;
        }

        private LectureLieu Lire(long cellId)
        {
            using (var client = new ClientLieu(port, Delai)) return client.Lire(cellId);
        }

        private LectureLieu Absence(long cellId)
        {
            LectureLieu lecture = Lire(cellId);
            Assert.IsFalse(lecture.Presente, "une réponse fautive ne rend jamais de lieu");
            Assert.IsNull(lecture.Lieu);
            Assert.IsNotNull(lecture.Absence);
            StringAssert.Contains("9922", lecture.Absence);
            return lecture;
        }

        private static string Sans(string texte, string retrait)
        {
            string prive = texte.Replace(retrait, "");
            Assert.AreNotEqual(texte, prive, "le retrait de " + retrait + " n'a rien changé");
            return prive;
        }

        [Test]
        public void UnLieuServiEstReluExactement()
        {
            Servir(200, TexteFige("lieu-graine0-tick3.json"));

            LectureLieu lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente);
            Assert.IsNull(lecture.Absence);
            Lieu lieu = lecture.Lieu;
            Assert.IsTrue(lieu.CellId == 9922);
            Assert.IsTrue(lieu.Tick == 3);
            Assert.IsTrue(lieu.Annee == 1400);
            Assert.IsTrue(lieu.JourDeLAnnee == 4);
            Assert.IsTrue(lieu.Population == 109741);
            Assert.IsTrue(lieu.HungerTicks == 0);
            Assert.IsTrue(lieu.FoodDeficitKg == 0.0, "0.0 est une mesure et se garde");
            CollectionAssert.AreEquivalent(new[] { "fer", "nourriture", "objet" }, lieu.Stocks.Keys.ToArray());
            Assert.IsTrue(lieu.Stocks["fer"] == 625.868635);
            Assert.IsTrue(lieu.Stocks["nourriture"] == 1092551.560271);
            Assert.IsTrue(lieu.Stocks["objet"] == 19.415619);
        }

        [Test]
        public void UnServiceDecaleDUnTickNePassePasPourLeBon()
        {
            Servir(200, TexteFige("lieu-graine0-tick4.json"));

            LectureLieu lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsTrue(lecture.Lieu.Tick == 4);
            Assert.AreNotEqual(1092551.560271, lecture.Lieu.Stocks["nourriture"]);
        }

        [Test]
        public void UneMarchandiseNouvellePasseEtUneAbsenteNEstPasInventee()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            string autre = Sans(texte, "\"fer\":625.868635,").Replace("\"stocks\":{", "\"stocks\":{\"zinc_du_test\":0.0,");
            Servir(200, autre);

            LectureLieu lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsFalse(lecture.Lieu.Stocks.ContainsKey("fer"), "une marchandise absente n'est jamais inventée à 0");
            Assert.IsTrue(lecture.Lieu.Stocks["zinc_du_test"] == 0.0, "0.0 reçu est une mesure");
            CollectionAssert.AreEquivalent(new[] { "zinc_du_test", "nourriture", "objet" }, lecture.Lieu.Stocks.Keys.ToArray());
        }

        [Test]
        public void UnPortFermeRendUneAbsenceQuiNommeLePort()
        {
            LectureLieu lecture = Absence(CellFigee);

            StringAssert.Contains("service absent", lecture.Absence);
            StringAssert.Contains(port.ToString(), lecture.Absence);
        }

        [Test]
        public void UnStatut404RendUneAbsenceOuLeClientNommeLaCellule()
        {
            const string corps = "{\"erreur\":\"inconnu\"}";
            StringAssert.DoesNotContain("9922", corps);
            Servir(404, corps);

            LectureLieu lecture = Absence(CellFigee);

            StringAssert.Contains("404", lecture.Absence);
            StringAssert.Contains(corps, lecture.Absence);
        }

        [Test]
        public void UneCleRetireeRendUneAbsenceQuiLaNomme()
        {
            Servir(200, Sans(TexteFige("lieu-graine0-tick3.json"), "\"population\":109741,"));

            StringAssert.Contains("population", Absence(CellFigee).Absence);
        }

        [Test]
        public void UneCleDeDateRetireeRendUneAbsenceQuiNommeSonChemin()
        {
            Servir(200, Sans(TexteFige("lieu-graine0-tick3.json"), "\"annee\":1400,"));

            StringAssert.Contains("date.annee", Absence(CellFigee).Absence);
        }

        [Test]
        public void UnTypeInattenduRendUneAbsenceQuiNommeLaCle()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            string altere = texte.Replace("\"fer\":625.868635", "\"fer\":\"beaucoup\"");
            Assert.AreNotEqual(texte, altere);
            Servir(200, altere);

            StringAssert.Contains("stocks.fer", Absence(CellFigee).Absence);
        }

        [Test]
        public void UnNombreNonEntierLaOuUnEntierEstAttenduEstRefuse()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            string altere = texte.Replace("\"population\":109741", "\"population\":109741.5");
            Assert.AreNotEqual(texte, altere);
            Servir(200, altere);

            StringAssert.Contains("clé population", Absence(CellFigee).Absence);
        }

        [Test]
        public void UnJsonInvalideRendUneAbsenceQuiNommeLaPosition()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            Assert.IsTrue(texte.EndsWith("}"));
            Servir(200, texte.Substring(0, texte.Length - 1));

            LectureLieu lecture = Absence(CellFigee);

            StringAssert.Contains("JSON invalide", lecture.Absence);
            StringAssert.Contains("position", lecture.Absence);
        }

        [Test]
        public void UneAutreCelluleRendUneAbsenceQuiNommeLesDeux()
        {
            Servir(200, TexteFige("lieu-graine0-tick3.json"));

            LectureLieu lecture = Lire(9923);

            Assert.IsFalse(lecture.Presente);
            Assert.IsNull(lecture.Lieu);
            StringAssert.Contains("9923", lecture.Absence);
            StringAssert.Contains("9922", lecture.Absence);
        }

        [Test]
        public void UneRedirectionNEstPasSuivie()
        {
            // Suivie, elle mènerait à un lieu valide : seul le refus de la suivre rend l'absence.
            Servir(200, TexteFige("lieu-graine0-tick3.json"), redirection: "/ailleurs");

            LectureLieu lecture = Absence(CellFigee);

            StringAssert.Contains("302", lecture.Absence);
        }

        [Test]
        public void UnEntierAuDelaDeDeuxPuissance53EstRefuse()
        {
            // 9007199254740993 se lit 9007199254740992 en double : accepté, il deviendrait un autre nombre.
            string texte = TexteFige("lieu-graine0-tick3.json");
            string altere = texte.Replace("\"population\":109741", "\"population\":9007199254740993");
            Assert.AreNotEqual(texte, altere);
            Servir(200, altere);

            StringAssert.Contains("clé population", Absence(CellFigee).Absence);
        }

        [Test]
        public void LePlusGrandEntierSurEstReluExactement()
        {
            // Contre-épreuve : juste sous 2^53, l'entier reste lu tel quel.
            string texte = TexteFige("lieu-graine0-tick3.json");
            string altere = texte.Replace("\"population\":109741", "\"population\":9007199254740991");
            Assert.AreNotEqual(texte, altere);
            Servir(200, altere);

            LectureLieu lecture = Lire(CellFigee);

            Assert.IsTrue(lecture.Presente, lecture.Absence);
            Assert.IsTrue(lecture.Lieu.Population == 9007199254740991L);
        }

        [Test]
        public void UnServiceMuetRendUneAbsenceDeDelaiDepasse()
        {
            Servir(200, TexteFige("lieu-graine0-tick3.json"), muet: true);

            LectureLieu lecture;
            using (var client = new ClientLieu(port, TimeSpan.FromMilliseconds(300)))
                lecture = client.Lire(CellFigee);

            Assert.IsFalse(lecture.Presente);
            Assert.IsNull(lecture.Lieu);
            StringAssert.Contains("9922", lecture.Absence);
            StringAssert.Contains("délai dépassé", lecture.Absence);
        }

        [Test]
        public void UnPortHorsBornesEstRefuse()
        {
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientLieu(0, Delai));
            Assert.Throws<ArgumentOutOfRangeException>(() => new ClientLieu(65536, Delai));
        }

        // Lot #263 — foyers et logement, relus tels quels. 9, 1 et 3 sont incohérents : un recalcul échoue.
        private const string FoyersTick3 = "\"foyers\":{\"mineurs\":{\"foyers\":2195,\"personnes\":10974},\"paysans\":{\"foyers\":19754,\"personnes\":98767}}";
        private static string Remplacer(string texte, string avant, string apres)
        { string altere = texte.Replace(avant, apres); Assert.AreNotEqual(texte, altere, avant); return altere; }
        private static string AvecLogement(string texte, string logement)
        { Assert.IsTrue(texte.EndsWith("}")); return texte.Substring(0, texte.Length - 1) + ",\"logement\":" + logement + "}"; }
        private Lieu Servi(string corps)
        { Servir(200, corps); LectureLieu lecture = Lire(CellFigee); Assert.IsTrue(lecture.Presente, lecture.Absence); return lecture.Lieu; }

        [Test]
        public void LesFoyersServisSontRelusDansLOrdreEtSansLogement()
        {
            Lieu lieu = Servi(TexteFige("lieu-graine0-tick3.json"));
            Assert.AreEqual(EtatFoyers.Servis, lieu.EtatFoyers);
            CollectionAssert.AreEqual(new[] { "mineurs", "paysans" }, lieu.Foyers.Keys.ToArray());
            Assert.IsTrue(lieu.Foyers["mineurs"].Foyers == 2195 && lieu.Foyers["mineurs"].Personnes == 10974);
            Assert.IsTrue(lieu.Foyers["paysans"].Foyers == 19754 && lieu.Foyers["paysans"].Personnes == 98767);
            Assert.IsNull(lieu.Logement);
            Fermer();
            PortLibre();
            Lieu suivant = Servi(TexteFige("lieu-graine0-tick4.json"));
            Assert.IsTrue(suivant.Foyers["mineurs"].Foyers == 2196 && suivant.Foyers["mineurs"].Personnes == 10977);
        }

        [TestCase("\"foyers\":-1", EtatFoyers.NonCalcules)]
        [TestCase("", EtatFoyers.Absents)]
        public void DesFoyersNonCalculesOuAbsentsSeDeclarent(string remplacement, EtatFoyers attendu)
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            Lieu lieu = Servi(remplacement == "" ? Remplacer(texte, FoyersTick3 + ",", "") : Remplacer(texte, FoyersTick3, remplacement));
            Assert.AreEqual(attendu, lieu.EtatFoyers);
            Assert.IsNull(lieu.Foyers);
        }

        [TestCase("{\"capacite\":9,\"loges\":1,\"sans_logis\":3}", 9L, 1L, 3L)]
        [TestCase("{\"capacite\":9,\"loges\":-1,\"sans_logis\":-1}", 9L, -1L, -1L)]
        public void LeLogementEstReluTelQuel(string logement, long capacite, long loges, long sansLogis)
        {
            Logement lu = Servi(AvecLogement(TexteFige("lieu-graine0-tick3.json"), logement)).Logement;
            Assert.IsNotNull(lu);
            Assert.IsTrue(lu.Capacite == capacite && lu.Loges == loges && lu.SansLogis == sansLogis);
        }

        [TestCase("\"foyers\":\"x\"", null, "foyers")]
        [TestCase("\"personnes\":1.5", null, "foyers.mineurs.personnes")]
        [TestCase("retrait", null, "foyers.mineurs.personnes")]
        [TestCase(null, "{\"capacite\":9,\"loges\":1}", "logement.sans_logis")]
        [TestCase(null, "3", "logement")]
        public void DesFoyersOuUnLogementMalFormesRendentUneAbsence(string foyers, string logement, string chemin)
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            string corps = foyers == null ? AvecLogement(texte, logement)
                : foyers == "retrait" ? Remplacer(texte, ",\"personnes\":10974", "")
                : foyers.StartsWith("\"personnes\"") ? Remplacer(texte, "\"personnes\":10974", foyers)
                : Remplacer(texte, FoyersTick3, foyers);
            Servir(200, corps);
            StringAssert.Contains(chemin, Absence(CellFigee).Absence);
        }

        // Lot #611 — rang, position et maître de chaque lieu, relus sans seconde clé.
        [Test] public void ChaqueLieuEstReluDansLOrdre()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            var attendus = (List<object>)LecteurJson.LireObjet(texte)["lieux"];
            var fournie = new List<LieuPlace> { new LieuPlace(4, new PointCarte(8, 9), "isole") };
            Lieu copie = new Lieu(1, 1, 1400, 1, 1, new Dictionary<string, double>(), 0, 0, lieux: fournie);
            fournie[0] = new LieuPlace(0, null, "autre"); fournie.Add(new LieuPlace(5, null, null));
            Assert.IsTrue(copie.Lieux.Count == 1 && copie.Lieux[0].Rang == 4 && copie.Lieux[0].Maitre == "isole" && copie.Lieux[0].Position.Value.X == 8 && copie.Lieux[0].Position.Value.Y == 9);
            Servir(200, texte);
            using (var client = new ClientLieu(port, Delai))
            {
                LectureLieu lecture = client.Lire(CellFigee);
                Assert.IsTrue(lecture.Presente && lecture.Lieu.Lieux.Count == attendus.Count && lecture.Lieu.Lieux.Count > 1 && lecture.Lieu.AbsenceDesLieux == null, lecture.Absence);
                var maitres = new HashSet<string>(); bool place = false; Lieu lieu = lecture.Lieu;
                for (int i = 0; i < attendus.Count; i++)
                {
                    var brut = (Dictionary<string, object>)attendus[i]; var point = (Dictionary<string, object>)brut["point"]; LieuPlace lu = lieu.Lieux[i];
                    Assert.IsTrue(lu.Rang == (long)(double)brut["rang"] && lu.Maitre == (string)brut["maitre"] && lu.Position.Value.X == (double)point["x_m"] && lu.Position.Value.Y == (double)point["y_m"]);
                    maitres.Add(lu.Maitre); place |= lu.Position.Value.X != 0 || lu.Position.Value.Y != 0;
                }
                Assert.IsTrue(maitres.Count > 1 && place);
                Assert.Throws<NotSupportedException>(() => ((IList<LieuPlace>)lieu.Lieux).Add(null));
                Fermer();
                Servir(200, texte.Replace("\"x_m\":4631943.28,\"y_m\":4046406.921", "\"x_m\":1.25,\"y_m\":-3.5").Replace("\"maitre\":\"plausible-9922-0\",\"nom\":\"\u00d6vre dal\"", "\"maitre\":\"maison-b\",\"nom\":\"\u00d6vre dal\""));
                Lieu relu = client.Lire(CellFigee).Lieu;
                Assert.IsTrue(relu.Lieux[1].Maitre == "maison-b" && relu.Lieux[1].Position.Value.X == 1.25 && relu.Lieux[1].Position.Value.Y == -3.5 && relu.Lieux[0].Position.Value.X == lieu.Lieux[0].Position.Value.X && relu.Lieux[0].Maitre == lieu.Lieux[0].Maitre);
            }
        }

        [Test] public void LesAbsencesDeLieuxRestentDistinctesDesMesures()
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            int crochet = texte.IndexOf("\"lieux\":[", StringComparison.Ordinal) + 8, fin = FinDelimitee(texte, crochet);
            string sans = texte.Remove(crochet - 8, fin + 1 - (crochet - 8));
            Assert.IsFalse(LecteurJson.LireObjet(sans).ContainsKey("lieux"));
            Lieu Voir(string corps) { Fermer(); Servir(200, corps); LectureLieu lecture = Lire(CellFigee); Assert.IsTrue(lecture.Presente, lecture.Absence); return lecture.Lieu; }
            Lieu absent = Voir(sans);
            Assert.IsTrue(absent.Lieux == null && absent.AbsenceDesLieux != null && absent.AbsenceDesLieux.Contains("lieux") && !absent.AbsenceDesLieux.Contains("lieux["));
            Lieu vide = Voir(texte.Substring(0, crochet) + "[]" + texte.Substring(fin));
            Assert.IsTrue(vide.Lieux != null && vide.Lieux.Count == 0 && vide.AbsenceDesLieux == null);
            LieuPlace declare = Voir(texte.Substring(0, crochet) + "[{\"rang\":2,\"point\":null,\"maitre\":null}]" + texte.Substring(fin)).Lieux[0];
            Assert.IsTrue(declare.Rang == 2 && declare.Position == null && declare.Maitre == null);
            LieuPlace mesure = Voir(texte.Substring(0, crochet) + "[{\"rang\":2,\"point\":{\"x_m\":0,\"y_m\":0},\"maitre\":\"seigneurie-1\"}]" + texte.Substring(fin)).Lieux[0];
            Assert.IsTrue(mesure.Position.Value.X == 0 && mesure.Position.Value.Y == 0 && mesure.Maitre == "seigneurie-1");
        }

        [TestCase("lieux-null", "clé lieux :")] [TestCase("lieux-objet", "clé lieux :")] [TestCase("entree", "clé lieux[1] :")]
        [TestCase("sans-rang", "lieux[1].rang")] [TestCase("sans-point", "lieux[1].point")] [TestCase("sans-maitre", "lieux[1].maitre")]
        [TestCase("sans-x", "lieux[1].point.x_m")] [TestCase("sans-y", "lieux[1].point.y_m")] [TestCase("rang-neg", "lieux[1].rang")]
        [TestCase("rang-frac", "lieux[1].rang")] [TestCase("rang-bool", "lieux[1].rang")] [TestCase("rang-grand", "lieux[1].rang")]
        [TestCase("rang-doublon", "lieux[1].rang")] [TestCase("point-bool", "lieux[1].point")] [TestCase("x-texte", "lieux[1].point.x_m")]
        [TestCase("maitre-nombre", "lieux[1].maitre")] [TestCase("maitre-blanc", "lieux[1].maitre")] [TestCase("json", "JSON invalide")]
        public void UneFauteDePlaceRefuseToutLeLieu(string cas, string chemin)
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            if (cas == "json")
            {
                string hors = texte.Replace("\"x_m\":4631943.28", "\"x_m\":1e309");
                Assert.AreNotEqual(texte, hors); Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(hors));
                Servir(200, hors); StringAssert.Contains(chemin, Absence(CellFigee).Absence); return;
            }
            string corps = Muter(texte, cas);
            Assert.AreNotEqual(texte, corps); Preuve(LecteurJson.LireObjet(corps), cas);
            Servir(200, corps); StringAssert.Contains(chemin, Absence(CellFigee).Absence);
        }

        private static int FinDelimitee(string t, int i)
        {
            char ouv = t[i], fer = ouv == '{' ? '}' : ']'; int p = 0;
            for (int k = i; k < t.Length; k++)
            {
                if (t[k] == '"') { for (k++; t[k] != '"'; k++) if (t[k] == '\\') k++; }
                else if (t[k] == ouv) p++; else if (t[k] == fer && --p == 0) return k + 1;
            }
            Assert.Fail(ouv.ToString()); return -1;
        }

        private static string Muter(string texte, string cas)
        {
            int crochet = texte.IndexOf("\"lieux\":[", StringComparison.Ordinal) + 8, finTableau = FinDelimitee(texte, crochet);
            if (cas == "lieux-null" || cas == "lieux-objet") return texte.Substring(0, crochet) + (cas == "lieux-null" ? "null" : "{\"a\":1}") + texte.Substring(finTableau);
            int debut = FinDelimitee(texte, crochet + 1) + 1; while (texte[debut] != '{') debut++;
            int fin = FinDelimitee(texte, debut); string lieu = texte.Substring(debut, fin - debut), neu;
            if (cas == "entree") neu = "null";
            else if (cas == "sans-point" || cas == "point-bool") neu = RemplacerObjet(lieu, "point", cas == "sans-point" ? null : "true");
            else
            {
                string ancien = cas == "sans-rang" ? ",\"rang\":1" : cas == "sans-maitre" ? "\"maitre\":\"plausible-9922-0\"," : cas == "sans-x" ? "\"x_m\":4631943.28," : cas == "sans-y" ? ",\"y_m\":4046406.921"
                    : cas == "x-texte" ? "\"x_m\":4631943.28" : cas.StartsWith("maitre") ? "\"maitre\":\"plausible-9922-0\"" : "\"rang\":1";
                string nouveau = cas == "sans-rang" || cas == "sans-maitre" || cas == "sans-x" || cas == "sans-y" ? "" : cas == "rang-neg" ? "\"rang\":-1" : cas == "rang-frac" ? "\"rang\":1.5"
                    : cas == "rang-bool" ? "\"rang\":true" : cas == "rang-grand" ? "\"rang\":9007199254740992" : cas == "rang-doublon" ? "\"rang\":0" : cas == "x-texte" ? "\"x_m\":\"ouest\"" : cas == "maitre-nombre" ? "\"maitre\":27" : "\"maitre\":\" \"";
                neu = lieu.Replace(ancien, nouveau);
            }
            Assert.AreNotEqual(lieu, neu); return texte.Substring(0, debut) + neu + texte.Substring(fin);
        }

        private static string RemplacerObjet(string lieu, string cle, string valeur)
        {
            int i = lieu.IndexOf("\"" + cle + "\":", StringComparison.Ordinal), v = i + cle.Length + 3, fin = FinDelimitee(lieu, v), debut = lieu[i - 1] == ',' ? i - 1 : i;
            if (valeur != null) return lieu.Substring(0, v) + valeur + lieu.Substring(fin);
            if (debut == i && lieu[fin] == ',') fin++;
            return lieu.Remove(debut, fin - debut);
        }

        private static void Preuve(Dictionary<string, object> racine, string cas)
        {
            if (cas == "lieux-null") { Assert.IsNull(racine["lieux"]); return; }
            if (cas == "lieux-objet") { Assert.IsTrue(racine["lieux"] is Dictionary<string, object>); return; }
            var lieux = (List<object>)racine["lieux"]; var premier = (Dictionary<string, object>)lieux[0];
            if (cas == "entree") { Assert.IsNull(lieux[1]); Assert.IsTrue(premier.ContainsKey("point")); return; }
            var second = (Dictionary<string, object>)lieux[1];
            bool metre = cas.EndsWith("-x") || cas.EndsWith("-y") || cas == "x-texte";
            var gauche = metre ? (Dictionary<string, object>)premier["point"] : premier;
            var droite = metre ? (Dictionary<string, object>)second["point"] : second;
            string cle = cas.Contains("maitre") ? "maitre" : cas.Contains("point") ? "point" : metre ? (cas.Contains("x") ? "x_m" : "y_m") : "rang";
            if (cas.StartsWith("sans")) { Assert.IsTrue(!droite.ContainsKey(cle) && gauche.ContainsKey(cle)); return; }
            object attendu = cas == "rang-neg" ? (object)(-1d) : cas == "rang-frac" ? 1.5d : cas == "rang-bool" || cas == "point-bool" ? true
                : cas == "rang-grand" ? 9007199254740992d : cas == "rang-doublon" ? premier["rang"] : cas == "x-texte" ? "ouest" : cas == "maitre-nombre" ? 27d : " ";
            Assert.AreEqual(attendu, droite[cle]);
        }

        // Lot #654 — témoin : le fichier tick3 dont chaque lieu reçoit un triplet distinct ; "" retire le bloc du second.
        private static (double Kg, long Partis, long Arrives) Triplet(int i) => i == 0 ? (1234.56789, 7L, 2L) : i == 1 ? (0.0, 0L, 11L) : (i + 0.5, i, 20L + i);

        private static string Bloc((double Kg, long Partis, long Arrives) t, string cle = null, string valeur = null)
        {
            var paires = new[] { ("preleve_kg", t.Kg.ToString("R", CultureInfo.InvariantCulture)), ("partis_personnes", t.Partis.ToString(CultureInfo.InvariantCulture)), ("arrives_personnes", t.Arrives.ToString(CultureInfo.InvariantCulture)) };
            return "{" + string.Join(",", paires.Where(p => p.Item1 != cle || valeur != "retrait").Select(p => "\"" + p.Item1 + "\":" + (p.Item1 == cle ? valeur : p.Item2))) + "}";
        }

        private static (int Debut, int Fin) Entree(string texte, int index)
        {
            int debut = texte.IndexOf("\"lieux\":[", StringComparison.Ordinal) + 9;
            for (int i = 0; i < index; i++) { debut = FinDelimitee(texte, debut); Assert.AreEqual(',', texte[debut], "lieux[" + i + "] suivi"); debut++; }
            return (debut, FinDelimitee(texte, debut));
        }

        private static string Temoin(string second = null)
        {
            string texte = TexteFige("lieu-graine0-tick3.json");
            for (int i = ((List<object>)LecteurJson.LireObjet(texte)["lieux"]).Count - 1; i >= 0; i--)
            {
                var (debut, fin) = Entree(texte, i);
                string valeur = i == 1 && second != null ? (second == "" ? null : second) : Bloc(Triplet(i));
                texte = texte.Substring(0, debut) + RemplacerObjet(texte.Substring(debut, fin - debut), "flux_30j", valeur) + texte.Substring(fin);
            }
            return texte;
        }

        // Les attentes viennent du texte servi, relu par le lecteur JSON générique : jamais du nouveau lecteur.
        private static void LieuxCommeLeTexte(Lieu lieu, string texte)
        {
            var racine = LecteurJson.LireObjet(texte); var attendus = (List<object>)racine["lieux"];
            Assert.IsTrue(lieu.CellId == (long)(double)racine["cell_id"] && lieu.Tick == (long)(double)racine["tick"] && lieu.AbsenceDesLieux == null);
            Assert.IsTrue(attendus.Count > 1 && lieu.Lieux.Count == attendus.Count, "échantillon de lieux");
            for (int i = 0; i < attendus.Count; i++)
            {
                var brut = (Dictionary<string, object>)attendus[i]; var point = (Dictionary<string, object>)brut["point"]; LieuPlace lu = lieu.Lieux[i];
                Assert.IsTrue(lu.Rang == (long)(double)brut["rang"] && lu.Maitre == (string)brut["maitre"] && lu.Position.Value.X == (double)point["x_m"] && lu.Position.Value.Y == (double)point["y_m"], "place du lieu " + i);
                if (brut.TryGetValue("flux_30j", out object bloc) && bloc is Dictionary<string, object> flux)
                    Assert.IsTrue(lu.AbsenceDesFlux == null && lu.Flux != null && lu.Flux.PreleveKg == (double)flux["preleve_kg"]
                        && lu.Flux.PartisPersonnes == (long)(double)flux["partis_personnes"] && lu.Flux.ArrivesPersonnes == (long)(double)flux["arrives_personnes"], "flux du lieu " + i);
                else Assert.IsTrue(lu.Flux == null && lu.AbsenceDesFlux != null && lu.AbsenceDesFlux.Contains("lieux[" + i + "].flux_30j"), "absence des flux du lieu " + i);
            }
        }

        [Test] public void ChaqueLieuGardeSesTroisFluxExacts()
        {
            string temoin = Temoin(), fixture = TexteFige("lieu-graine0-tick3.json");
            var lieux = (List<object>)LecteurJson.LireObjet(temoin)["lieux"];
            Assert.AreEqual(lieux.Count, Enumerable.Range(0, lieux.Count).Select(Triplet).Distinct().Count(), "des triplets distincts");
            for (int i = 0; i < lieux.Count; i++)
            {
                var flux = (Dictionary<string, object>)((Dictionary<string, object>)lieux[i])["flux_30j"]; var t = Triplet(i);
                Assert.IsTrue((double)flux["preleve_kg"] == t.Kg && (double)flux["partis_personnes"] == t.Partis && (double)flux["arrives_personnes"] == t.Arrives, "témoin du lieu " + i);
            }
            Lieu lieu = Servi(temoin);
            LieuxCommeLeTexte(lieu, temoin);
            FluxDeLieu bourg = lieu.Lieux[0].Flux, second = lieu.Lieux[1].Flux;
            Assert.IsTrue(bourg.PreleveKg == 1234.56789 && bourg.PartisPersonnes == 7 && bourg.ArrivesPersonnes == 2 && second.PreleveKg == 0.0 && second.PartisPersonnes == 0 && second.ArrivesPersonnes == 11);
            Fermer();
            LieuxCommeLeTexte(Servi(fixture), fixture);
        }

        [TestCase("", "clé absente")] [TestCase("null", "null déclaré")]
        public void UneAbsenceDeFluxResteDistincteDesZeros(string bloc, string cause)
        {
            string corps = Temoin(bloc);
            var second = (Dictionary<string, object>)((List<object>)LecteurJson.LireObjet(corps)["lieux"])[1];
            Assert.IsTrue(bloc == "" ? !second.ContainsKey("flux_30j") : second.ContainsKey("flux_30j") && second["flux_30j"] == null);
            Lieu lieu = Servi(corps);
            LieuxCommeLeTexte(lieu, corps);
            string absence = lieu.Lieux[1].AbsenceDesFlux;
            Assert.IsTrue(absence.Contains(cause) && absence.Contains("absente") == (bloc == "") && absence.Contains("null") == (bloc == "null"), absence);
            Assert.IsTrue(lieu.Lieux[0].Flux.PreleveKg == 1234.56789 && lieu.Lieux[0].Flux.PartisPersonnes == 7 && lieu.Lieux[0].Flux.ArrivesPersonnes == 2);
        }

        [Test] public void TroisZerosServisSontDesMesures()
        {
            string corps = Temoin("{\"preleve_kg\":0.0,\"partis_personnes\":0,\"arrives_personnes\":0}");
            Lieu lieu = Servi(corps);
            LieuxCommeLeTexte(lieu, corps);
            FluxDeLieu zeros = lieu.Lieux[1].Flux;
            Assert.IsTrue(zeros != null && zeros.PreleveKg == 0 && zeros.PartisPersonnes == 0 && zeros.ArrivesPersonnes == 0 && lieu.Lieux[1].AbsenceDesFlux == null);
        }

        private static IEnumerable<TestCaseData> FluxFautifs()
        {
            foreach (string bloc in new[] { "[]", "\"beaucoup\"", "true", "{}" }) yield return new TestCaseData("", bloc);
            foreach (string cle in new[] { "preleve_kg", "partis_personnes", "arrives_personnes" })
                foreach (string valeur in new[] { "retrait", "null", "\"x\"", "false", "-1" }.Concat(cle == "preleve_kg" ? new[] { "1e309" } : new[] { "1.5", "9007199254740992" }))
                    yield return new TestCaseData(cle, valeur);
        }

        [TestCaseSource(nameof(FluxFautifs))]
        public void UnBlocDeFluxFautifRefuseToutLeLieu(string cle, string valeur)
        {
            string temoin = Temoin(), corps = Temoin(cle == "" ? valeur : Bloc(Triplet(1), cle, valeur));
            // La mutation ne touche que le bloc du second lieu : préfixe et suffixe communs l'encadrent.
            int debut = temoin.IndexOf("\"flux_30j\":", Entree(temoin, 1).Debut, StringComparison.Ordinal) + 11, fin = FinDelimitee(temoin, debut), court = Math.Min(temoin.Length, corps.Length), p = 0, s = 0;
            while (p < court && temoin[p] == corps[p]) p++;
            while (s < court - p && temoin[temoin.Length - 1 - s] == corps[corps.Length - 1 - s]) s++;
            Assert.IsTrue(temoin != corps && debut < Entree(temoin, 1).Fin && p >= debut && temoin.Length - s <= fin, "la mutation sort de lieux[1].flux_30j");
            string chemin = "lieux[1].flux_30j" + (cle != "" ? "." + cle : valeur == "{}" ? ".preleve_kg" : "");
            if (valeur == "1e309") { Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(corps)); chemin = "JSON invalide"; }
            else
            {
                object bloc = ((Dictionary<string, object>)((List<object>)LecteurJson.LireObjet(corps)["lieux"])[1])["flux_30j"];
                var d = bloc as Dictionary<string, object>;
                if (cle == "") Assert.AreEqual(valeur == "{}", d != null && d.Count == 0);
                else Assert.IsTrue(d.Count == (valeur == "retrait" ? 2 : 3) && d.ContainsKey(cle) == (valeur != "retrait")
                    && (valeur == "retrait" || Equals(LecteurJson.LireObjet("{\"v\":" + valeur + "}")["v"], d[cle])));
                chemin = valeur == "retrait" || valeur == "{}" ? "clé absente : " + chemin : "clé " + chemin + " :";
            }
            Servir(200, corps);
            StringAssert.Contains(chemin, Absence(CellFigee).Absence);
            Fermer();
            Assert.IsNotNull(Servi(temoin).Lieux[1].Flux, "restaurer le témoin rend une lecture présente");
        }

        [Test] public void LaNouvelleLectureDesFluxRemplaceLaPrecedente()
        {
            string[] corps = { Temoin(), Temoin("{\"preleve_kg\":0.25,\"recu_kg\":5,\"partis_personnes\":9007199254740991,\"arrives_personnes\":3}"), Temoin("") };
            var lus = new List<Lieu>();
            using (var client = new ClientLieu(port, Delai))
                foreach (string c in corps)
                {
                    Fermer(); Servir(200, c);
                    LectureLieu lecture = client.Lire(CellFigee);
                    Assert.IsTrue(lecture.Presente, lecture.Absence);
                    LieuxCommeLeTexte(lecture.Lieu, c); lus.Add(lecture.Lieu);
                }
            FluxDeLieu avant = lus[0].Lieux[1].Flux, change = lus[1].Lieux[1].Flux;
            Assert.IsTrue(avant.PreleveKg == 0.0 && avant.PartisPersonnes == 0 && avant.ArrivesPersonnes == 11, "la première lecture garde ses flux");
            Assert.IsTrue(change.PreleveKg == 0.25 && change.PartisPersonnes == 9007199254740991L && change.ArrivesPersonnes == 3 && lus[2].Lieux[1].Flux == null);
            foreach (Lieu lu in lus)
                Assert.IsTrue(lu.Lieux[0].Flux.PreleveKg == 1234.56789 && lu.Lieux[0].Flux.PartisPersonnes == 7 && lu.Lieux[0].Flux.ArrivesPersonnes == 2, "le premier lieu ne change pas");
        }

        // Lot #783 — témoin : le fichier tick3 dont `lieux` est remplacé ; `population` null retire la clé.
        private static string AvecLieux(params string[] places)
        { string texte = TexteFige("lieu-graine0-tick3.json"); int crochet = texte.IndexOf("\"lieux\":[", StringComparison.Ordinal) + 8; return texte.Substring(0, crochet) + "[" + string.Join(",", places) + "]" + texte.Substring(FinDelimitee(texte, crochet)); }

        private static string Place(long rang, string population) => "{\"rang\":" + rang + ",\"point\":null,\"maitre\":null" + (population == null ? "" : ",\"population\":" + population) + "}";

        [Test] public void ChaqueLieuGardeSaPopulationEtLeBourgSeTrouveParSonRang()
        {
            string corps = AvecLieux(Place(2, "9007199254740991"), Place(0, "4321"), Place(1, "0"), Place(3, null));
            var racine = LecteurJson.LireObjet(corps); var bruts = (List<object>)racine["lieux"];
            Assert.IsTrue((double)((Dictionary<string, object>)bruts[1])["rang"] == 0 && (double)racine["population"] == 109741 && !((Dictionary<string, object>)bruts[3]).ContainsKey("population"));
            Lieu lieu = Servi(corps);
            long?[] attendues = { 9007199254740991L, 4321, 0, null };
            for (int i = 0; i < attendues.Length; i++)
                Assert.IsTrue(lieu.Lieux[i].Population == attendues[i] && (lieu.Lieux[i].AbsenceDePopulation == null) == (attendues[i] != null), "population du lieu " + i);
            StringAssert.Contains("lieux[3].population", lieu.Lieux[3].AbsenceDePopulation);
            Assert.IsTrue(lieu.Bourg.Rang == 0 && lieu.Bourg.Population == 4321 && lieu.Population == 109741, "le bourg est le rang 0, pas la cellule ni la première entrée");
            Fermer(); Lieu sansBourg = Servi(AvecLieux(Place(1, "5"), Place(2, "6")));
            Assert.IsTrue(sansBourg.Bourg == null && sansBourg.Lieux[0].Population == 5 && sansBourg.Lieux[1].Population == 6);
            Fermer(); Lieu muet = Servi(AvecLieux(Place(1, "5"), Place(0, null)));
            Assert.IsTrue(muet.Bourg.Population == null && muet.Bourg.AbsenceDePopulation.Contains("lieux[1].population") && muet.Population == 109741);
            Fermer(); Lieu vide = Servi(AvecLieux());
            Assert.IsTrue(vide.Lieux.Count == 0 && vide.Bourg == null && vide.AbsenceDesLieux == null);
            LieuPlace ancienne = new LieuPlace(0, null, null);
            Assert.IsTrue(ancienne.Population == null && ancienne.AbsenceDePopulation != null, "un ancien constructeur ne fabrique pas de zéro");
        }

        [TestCase("null")] [TestCase("-1")] [TestCase("1.5")] [TestCase("true")] [TestCase("\"4321\"")] [TestCase("9007199254740992")]
        public void UnePopulationDeLieuFautiveRefuseToutLeLieu(string valeur)
        {
            string corps = AvecLieux(Place(2, "40"), Place(0, valeur));
            var second = (Dictionary<string, object>)((List<object>)LecteurJson.LireObjet(corps)["lieux"])[1];
            Assert.IsTrue(second.ContainsKey("population") && Equals(LecteurJson.LireObjet("{\"v\":" + valeur + "}")["v"], second["population"]), "la mutation touche lieux[1].population");
            Servir(200, corps);
            StringAssert.Contains("clé lieux[1].population :", Absence(CellFigee).Absence);
        }

        // Lot #778 — un faux service qui note chaque demande et répond selon elle ; null ne répond jamais.
        private readonly List<string> demandes = new List<string>();
        private void Repondre(Func<string, (int Statut, string Corps)?> reponse)
        {
            demandes.Clear(); ecoute = new HttpListener(); ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/"); ecoute.Start(); var auditeur = ecoute;
            fil = new Thread(() => { while (true) {
                HttpListenerContext c; try { c = auditeur.GetContext(); } catch (Exception) { return; }
                lock (demandes) demandes.Add(c.Request.Url.PathAndQuery);
                var r = reponse(c.Request.Url.PathAndQuery); if (r == null) continue;
                byte[] octets = Encoding.UTF8.GetBytes(r.Value.Corps); c.Response.StatusCode = r.Value.Statut;
                if (r.Value.Statut == 302) c.Response.RedirectLocation = "http://127.0.0.1:" + port + "/ailleurs";
                c.Response.ContentLength64 = octets.Length; c.Response.OutputStream.Write(octets, 0, octets.Length); c.Response.OutputStream.Close(); } }) { IsBackground = true };
            fil.Start();
        }
        // Témoins : le bloc local diffère toujours des chiffres cellulaires (faim, population, panier).
        private static string Bourg(string stocks = "\"fer\":0.0,\"nourriture\":12.345678901,\"sel_futur\":0.75", long faim = 3, long faimCellule = 0, long tick = 17) =>
            "{\"bourg\":{\"duree_faim_ticks\":" + faim + ",\"population\":4321,\"rang\":0,\"stocks\":{" + stocks + "},\"tick\":" + tick + "},\"cell_id\":9922,\"date\":{\"annee\":1400,\"jour_de_l_annee\":" + (tick + 1)
            + "},\"hunger_ticks\":" + faimCellule + ",\"lieux\":[],\"population\":109741,\"stocks\":{\"fer\":625.868635,\"nourriture\":1092551.560271},\"tick\":" + tick + "}";
        private const string Maisons = "{\"capacite\":4,\"identifiant\":2,\"loges\":4},{\"capacite\":3,\"identifiant\":5,\"loges\":1},{\"capacite\":2,\"identifiant\":9,\"loges\":0}";
        private static string Occupation(string ilots = "{\"foyers\":3,\"rang\":0},{\"foyers\":1,\"rang\":1}", string maisons = Maisons, string logement = "{\"capacite\":9,\"loges\":5,\"sans_logis\":0}", long tick = 17) =>
            "{\"base\":[" + ilots + "],\"batiments\":[" + maisons + "],\"cell_id\":9922,\"date\":{\"annee\":1400,\"jour_de_l_annee\":" + (tick + 1) + "},\"logement\":" + logement + ",\"rang\":0,\"tick\":" + tick + "}";
        private static T Lue<T>(Lecture<T> lecture) where T : class { Assert.IsTrue(lecture.Presente && lecture.Absence == null, lecture.Absence); return lecture.Donnees; }
        private static void Absente<T>(Lecture<T> lecture, params string[] morceaux) where T : class
        { Assert.IsTrue(!lecture.Presente && lecture.Donnees == null && lecture.Absence.Contains("9922"), lecture.Absence); foreach (string m in morceaux) StringAssert.Contains(m, lecture.Absence); }
        private Lecture<T> Vie<T>(Func<ClientVieDuBourg, Lecture<T>> lire) where T : class { using (var client = new ClientVieDuBourg(port, Delai)) return lire(client); }

        [TestCase("\"fer\":0.0,\"nourriture\":12.345678901,\"sel_futur\":0.75", 3, 0)] [TestCase("\"fer\":0.0,\"nourriture\":12.345678901,\"sel_futur\":0.75", 0, 5)]
        [TestCase("\"fer\":0.0,\"nourriture\":0.0", 0, 0)] [TestCase("\"nourriture\":12.345678901,\"sel_futur\":0.75", 3, 0)]
        public void LeBourgEstReluExactement(string stocks, long faim, long faimCellule)
        {
            string corps = Bourg(stocks, faim, faimCellule); Repondre(_ => (200, corps));
            BourgLu b = Lue(Vie(c => c.LireBourg(CellFigee)));
            var attendus = (Dictionary<string, object>)((Dictionary<string, object>)LecteurJson.LireObjet(corps)["bourg"])["stocks"];
            CollectionAssert.AreEqual(new[] { "/lieu?cell=9922&bourg=1" }, demandes);
            Assert.IsTrue(b.CellId == 9922 && b.Rang == 0 && b.Tick == 17 && b.TickLocal == 17 && b.Date.Annee == 1400 && b.Date.JourDeLAnnee == 18 && b.Population == 4321 && b.DureeFaimTicks == faim);
            CollectionAssert.AreEquivalent(attendus.Keys, b.Stocks.Keys);
            foreach (var m in attendus) Assert.IsTrue(b.Stocks[m.Key] == (double)m.Value, m.Key);
            Assert.IsTrue(b.Stocks.ContainsKey("fer") == stocks.Contains("fer"), "une marchandise retirée reste absente");
            Assert.Throws<NotSupportedException>(() => ((IDictionary<string, double>)b.Stocks).Add("x", 1));
        }

        [TestCase("temoin", "0:3 1:1|2/4/4 5/3/1 9/2/0|9/5/0")] [TestCase("null", "0:3 1:1||null")]
        [TestCase("non-calcules", "0:3 1:1|2/4/-1 5/3/-1 9/2/-1|9/-1/-1")] [TestCase("vide", "||0/0/0")]
        public void LesMaisonsGardentLeursComptesServis(string cas, string attendu)
        {
            string corps = cas == "temoin" ? Occupation() : cas == "null" ? Occupation(maisons: "", logement: "null") : cas == "vide" ? Occupation("", "", "{\"capacite\":0,\"loges\":0,\"sans_logis\":0}")
                : Occupation(maisons: Maisons.Replace("\"loges\":4", "\"loges\":-1").Replace("\"loges\":1", "\"loges\":-1").Replace("\"loges\":0", "\"loges\":-1"), logement: "{\"capacite\":9,\"loges\":-1,\"sans_logis\":-1}");
            Repondre(_ => (200, corps));
            OccupationLue o = Lue(Vie(c => c.LireOccupation(CellFigee)));
            CollectionAssert.AreEqual(new[] { "/occupation?cell=9922" }, demandes);
            Assert.IsTrue(o.CellId == 9922 && o.Rang == 0 && o.Tick == 17 && o.Date.JourDeLAnnee == 18);
            string lu = string.Join(" ", o.Base.Select(i => i.Rang + ":" + i.Foyers)) + "|" + string.Join(" ", o.Batiments.Select(m => m.Identifiant + "/" + m.Capacite + "/" + m.Loges))
                + "|" + (o.Logement == null ? "null" : o.Logement.Capacite + "/" + o.Logement.Loges + "/" + o.Logement.SansLogis);
            Assert.AreEqual(attendu, lu);
            Assert.AreEqual(cas == "null" || cas == "non-calcules", o.RaisonDuLogement != null, o.RaisonDuLogement);
            Assert.Throws<NotSupportedException>(() => ((IList<(long, long)>)o.Base).Add((9, 9)));
        }

        private static string Json(object v) => v == null ? "null" : v is bool b ? (b ? "true" : "false") : v is double d ? d.ToString("R", CultureInfo.InvariantCulture) : v is string s ? "\"" + s + "\""
            : v is List<object> l ? "[" + string.Join(",", l.Select(Json)) + "]" : "{" + string.Join(",", ((Dictionary<string, object>)v).Select(p => "\"" + p.Key + "\":" + Json(p.Value))) + "}";
        // `chemin` : clés séparées par des points, `[i]` pour un indice ; "retrait" retire la clé. Le corps rendu reste un JSON valide et diffère du témoin.
        private static string Muter(string temoin, string chemin, object valeur)
        {
            var racine = LecteurJson.LireObjet(temoin); object parent = racine; string[] pas = chemin.Replace("[", ".[").Split('.'); string fin = pas[pas.Length - 1];
            for (int i = 0; i < pas.Length - 1; i++) parent = pas[i].StartsWith("[") ? ((List<object>)parent)[int.Parse(pas[i].Trim('[', ']'))] : ((Dictionary<string, object>)parent)[pas[i]];
            if (fin.StartsWith("[")) ((List<object>)parent)[int.Parse(fin.Trim('[', ']'))] = valeur;
            else if (Equals(valeur, "retrait")) Assert.IsTrue(((Dictionary<string, object>)parent).Remove(fin), chemin); else ((Dictionary<string, object>)parent)[fin] = valeur;
            string corps = Json(racine); Assert.AreNotEqual(Json(LecteurJson.LireObjet(temoin)), corps, chemin); LecteurJson.LireObjet(corps); return corps;
        }
        private static IEnumerable<TestCaseData> FautesDeVie()
        {
            foreach (string c in new[] { "cell_id", "tick", "date", "date.annee", "date.jour_de_l_annee", "bourg", "bourg.rang", "bourg.population", "bourg.stocks", "bourg.duree_faim_ticks", "bourg.tick" })
                yield return new TestCaseData(true, c, "retrait");
            foreach (string c in new[] { "cell_id", "rang", "tick", "date", "date.annee", "date.jour_de_l_annee", "base", "base[1].rang", "base[1].foyers", "batiments", "batiments[1].identifiant", "batiments[1].capacite", "batiments[1].loges", "logement", "logement.capacite", "logement.loges", "logement.sans_logis" })
                yield return new TestCaseData(false, c, "retrait");
            object[][] alterations = { new object[] { true, "cell_id", 9923d }, new object[] { true, "bourg.rang", 1d }, new object[] { true, "bourg.tick", 16d }, new object[] { true, "bourg.stocks.fer", -0.5 }, new object[] { true, "bourg.stocks.sel_futur", null },
                new object[] { true, "bourg.population", -1d }, new object[] { true, "tick", 17.5 }, new object[] { true, "bourg.duree_faim_ticks", 9007199254740992d }, new object[] { true, "bourg.stocks", "x" }, new object[] { true, "date.jour_de_l_annee", 0d },
                new object[] { false, "cell_id", 9921d }, new object[] { false, "rang", 1d }, new object[] { false, "tick", -1d }, new object[] { false, "base", true }, new object[] { false, "base[1].rang", 0d }, new object[] { false, "base[1].rang", 2d },
                new object[] { false, "base[0].foyers", 0d }, new object[] { false, "batiments[0]", "x" }, new object[] { false, "batiments[1].identifiant", 2d }, new object[] { false, "batiments[0].capacite", 9007199254740992d },
                new object[] { false, "batiments[2].capacite", 1.5 }, new object[] { false, "batiments[2].loges", 3d }, new object[] { false, "batiments[1].loges", -1d }, new object[] { false, "logement.sans_logis", -1d },
                new object[] { false, "logement.loges", 6d }, new object[] { false, "logement.capacite", 10d }, new object[] { false, "logement", null }, new object[] { false, "logement", "x" } };
            foreach (object[] a in alterations) yield return new TestCaseData(a);
            yield return new TestCaseData(true, "json", null); yield return new TestCaseData(false, "json", null);
        }
        [TestCaseSource(nameof(FautesDeVie))]
        public void ChaqueFauteDuBourgNommeSonCheminSansResultatPartiel(bool bourg, string chemin, object valeur)
        {
            string temoin = bourg ? Bourg() : Occupation(), corps = chemin == "json" ? Remplacer(temoin, "\"jour_de_l_annee\":18", "\"jour_de_l_annee\":1e309") : Muter(temoin, chemin, valeur), servi = corps;
            if (chemin == "json") Assert.Throws<ErreurJson>(() => LecteurJson.LireObjet(corps));
            string attendu = chemin == "json" ? "JSON invalide" : Equals(valeur, "retrait") ? "clé absente : " + chemin : "clé " + chemin + " :";
            Repondre(_ => (200, servi));
            using (var client = new ClientVieDuBourg(port, Delai))
            {
                if (bourg) Absente(client.LireBourg(CellFigee), attendu); else Absente(client.LireOccupation(CellFigee), attendu);
                servi = temoin;
                Assert.IsTrue(bourg ? Lue(client.LireBourg(CellFigee)).Stocks["fer"] == 0.0 : Lue(client.LireOccupation(CellFigee)).Batiments[2].Loges == 0, "le témoin intact passe");
            }
        }

        [Test] public void DesCapacitesDontLaSommeDeborderaitVers1SontRefusees() // 2 048 × (2^53−1) + 2 049 = 2^64 + 1, soit 1 en long
        {
            string corps = Occupation(maisons: string.Join(",", Enumerable.Range(1, 2049).Select(i => "{\"capacite\":" + (i < 2049 ? "9007199254740991" : "2049") + ",\"identifiant\":" + i + ",\"loges\":0}")), logement: "{\"capacite\":1,\"loges\":0,\"sans_logis\":0}");
            Repondre(_ => (200, corps)); Absente(Vie(c => c.LireOccupation(CellFigee)), "clé batiments[1].capacite :", "sous 2^53");
        }
        [Test] public void ChaquePublicationGardeSonJourEtChaqueEchecSaCause()
        {
            (int, string)? bourg = (200, Bourg()), occupation = (200, Occupation()); bool muet = false;
            Repondre(d => muet ? null : d.StartsWith("/lieu") ? bourg : occupation);
            using (var client = new ClientVieDuBourg(port, TimeSpan.FromMilliseconds(500)))
            {
                BourgLu b1 = Lue(client.LireBourg(CellFigee)); OccupationLue o1 = Lue(client.LireOccupation(CellFigee));
                bourg = (200, Bourg("\"nourriture\":2.5", 4, 0, 30)); occupation = (200, Occupation(maisons: Maisons.Replace("\"loges\":1", "\"loges\":3"), logement: "{\"capacite\":9,\"loges\":7,\"sans_logis\":2}", tick: 31));
                BourgLu b2 = Lue(client.LireBourg(CellFigee)); OccupationLue o2 = Lue(client.LireOccupation(CellFigee));
                Assert.IsTrue(b1.Tick == 17 && b1.Stocks.Count == 3 && b1.DureeFaimTicks == 3 && o1.Tick == 17 && o1.Logement.Loges == 5 && o1.Batiments[1].Loges == 1, "la première lecture garde ses valeurs");
                Assert.IsTrue(b2.Tick == 30 && b2.TickLocal == 30 && b2.Date.JourDeLAnnee == 31 && b2.DureeFaimTicks == 4 && b2.Stocks.Count == 1 && b2.Stocks["nourriture"] == 2.5);
                Assert.IsTrue(o2.Tick == 31 && o2.Date.JourDeLAnnee == 32 && o2.Logement.Loges == 7 && o2.Logement.SansLogis == 2 && o2.Batiments[1].Loges == 3, "chaque route garde son propre tick");
                foreach (var (statut, corps, cause) in new[] { (404, "{\"erreur\":\"inconnu\"}", "statut 404"), (500, "{\"erreur\":\"panne du tick\"}", "panne du tick"), (302, "", "statut 302") })
                { bourg = occupation = (statut, corps); Absente(client.LireBourg(CellFigee), "bourg", cause); Absente(client.LireOccupation(CellFigee), "occupation", cause); }
                bourg = (200, Bourg()); occupation = (200, Occupation());
                Assert.IsTrue(Lue(client.LireBourg(CellFigee)).Tick == 17 && Lue(client.LireOccupation(CellFigee)).Logement.Loges == 5, "un succès se relit après un échec");
                muet = true;
                Absente(client.LireBourg(CellFigee), "délai dépassé"); Absente(client.LireOccupation(CellFigee), "délai dépassé");
            }
            Assert.IsFalse(demandes.Contains("/ailleurs"), "le 302 n'est pas suivi");
            Fermer();
            Absente(Vie(c => c.LireBourg(CellFigee)), "service absent"); Absente(Vie(c => c.LireOccupation(CellFigee)), "service absent");
        }
    }
}
