using System;
using System.Collections.Generic;
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
    }
}
