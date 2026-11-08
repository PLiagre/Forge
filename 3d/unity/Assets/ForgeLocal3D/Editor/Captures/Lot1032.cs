using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 1032 : la barre du haut porte les trois jauges et les trois réserves de points du pays, lues sur `/pays` au tick du monde lu.
    // Trois scénarios, joués dans l'ordre de leur nom, sur le même service et la même carte :
    //   1. le petit seigneur : Bar-le-Duc choisi, trente jours de points (ou, avec `-forge1032Depense`, un geste du Sceau et le Droit qui monte) ;
    //   2. le royaume : le suzerain de Bar, posé côté Unity (le monde ne laisse pas encore prendre un royaume, #1037) ;
    //   3. le Zab : la maison `seigneurie-6`, dont le monde ne connaît pas le chef.
    // Le texte attendu de chaque cellule s'écrit ici, depuis une lecture indépendante de `/pays`, sans appeler `BarreDuPays`.
    // Contre-épreuve : `-forge1032Avance` pousse un tick avant de juger la première lecture : la barre est restée au tick d'avant, le scénario échoue.
    static class Lot1032
    {
        const string AVANCE = "-forge1032Avance", DEPENSE = "-forge1032Depense", TICKS_ARG = "-forgeTicks";
        const string SIEGE = "Bar-le-Duc", SANS_CHEF = "seigneurie-6", NOM_SANS_CHEF = "Banou Mozni";
        const string BANDEAU = "FORGE · Le cabinet", CONTENEUR = "Jauges du pays", BAISSE = ", en baisse", HAUSSE = ", en hausse";
        const int IMAGES = 10, TICKS = 30;
        // Les clés servies par `/pays`, et le nom de la cellule de la barre qui montre chacune (les trois jauges, puis les trois réserves).
        static readonly string[] CLES = { "concorde", "renom", "droit", "plume", "sceau", "epee" };
        static readonly string[] CELLULES = { "Concorde", "Renom", "Droit", "Plume", "Sceau", "Épée" };
        static readonly CultureInfo Fr = CultureInfo.GetCultureInfo("fr-FR"), Inv = CultureInfo.InvariantCulture;

        static CarteDessinee carte;
        static CabinetDeCarte cabinet;
        static Transform toile, conteneur;
        static int port;
        static string bar;

        // Ce que la barre doit montrer à un tick : le pays servi, la valeur de chaque cellule et son texte attendu.
        sealed class Releve
        {
            public PaysLu Pays;
            public readonly Dictionary<string, double> Valeurs = new Dictionary<string, double>();
            public readonly string[] Textes = new string[6];
        }

        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string N(long? v) => v == null ? "non servi" : v.Value.ToString(Inv);
        static string Pts(double v) => TexteDuMonde.Points(v);
        static string Ligne(string t) => t == null ? "(aucun)" : t.Replace("\r", "").Replace("\n", " | ");
        static bool Drapeau(string nom) => Environment.GetCommandLineArgs().Contains(nom);
        static string Signe(double pourcent) => (pourcent > 0 ? "+" : "") + pourcent.ToString("0.##", Fr);

        // Le parcours part du tick demandé au service : `-forgeTicks`, sinon le défaut de `ForgeCapture` (30), comme `Lot658`.
        static long Depart()
        {
            var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, TICKS_ARG);
            return i >= 0 && i + 1 < a.Length ? long.Parse(a[i + 1], Inv) : 30;
        }

        [ScenarioDeCapture(1032, "barre-1-petit-seigneur")]
        static IEnumerator PetitSeigneur(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null; // étape 1
            carte = ouverte.Carte; port = carte.port;
            cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : pas de CabinetDeCarte");
            toile = carte.transform.Find("Cabinet") ?? throw Echec("étape 1 : pas de toile du cabinet");
            conteneur = toile.Find(BANDEAU + "/" + CONTENEUR) ?? throw Echec("étape 1 : « " + CONTENEUR + " » introuvable dans le bandeau");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 2 : partie " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null; // étape 2
            // La toile sur la caméra de la photo, comme `Lot658` : les jugements de cadre se font sur ce que l'image montre.
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f);
            var canvas = toile.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera; canvas.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases();

            var partie = cabinet.Partie; long depart = Depart(), tick = partie.Monde.Donnees.Monde.Tick;
            if (tick != depart) throw Echec("étape 3 : tick initial " + N(tick) + ", attendu " + N(depart) + " (" + TICKS_ARG + ")");
            var fiches = partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (fiches.Length != 1) throw Echec("étape 3 : " + fiches.Length + " départs dont le siège est « " + SIEGE + " »");
            var choix = partie.Choisir(fiches[0].Id);
            for (var e = Lot690.Attendre(choix, "choix de " + SIEGE); e.MoveNext();) yield return null;
            if (partie.Recu == null || !partie.Recu.Acceptee) throw Echec("étape 3 : reçu du choix refusé : " + (partie.Recu == null ? "aucun reçu" : partie.Recu.Presente ? partie.Recu.Erreur : partie.Recu.Absence));
            for (var e = Pousser(1); e.MoveNext();) yield return null;
            for (var e = Prete(null, tick + 1, "étape 3"); e.MoveNext();) yield return null;
            bar = cabinet.Partie.Monde.Donnees.MaisonDuJoueur;

            // Lecture R1 : dans la même image que la relecture, sans yield. Avec l'avance, un tick passe avant : la barre est restée au tick d'avant.
            if (Drapeau(AVANCE)) { var un = Lot690.PousserTick(port).Result; if (un.statut != 200) throw Echec("étape 4 : tick " + un.corps); }
            Releve r1 = Juger(camera, bar, "étape 4, lecture R1", null);

            bool depense = Drapeau(DEPENSE);
            if (depense)
            {
                RecuIntention recu;
                using (var client = new ClientIntention(port, TimeSpan.FromSeconds(10)))
                    recu = client.Deposer("{\"type\":\"depenser_jauge\",\"maison\":\"" + bar + "\",\"geste\":\"asseoir_le_droit\"}");
                if (!recu.Acceptee) throw Echec("étape 5 : la dépense est refusée : " + (recu.Presente ? recu.Erreur : recu.Absence));
                for (var e = Pousser(1); e.MoveNext();) yield return null;
            }
            else for (var e = Pousser(TICKS); e.MoveNext();) yield return null;
            long apres = r1.Pays.Tick + (depense ? 1 : TICKS);
            for (var e = Prete(bar, apres, "étape 5"); e.MoveNext();) yield return null;
            Releve r2 = Juger(camera, bar, "étape 6, lecture R2", r1);

            if (depense)
            {
                if (r2.Textes[4] != "Sceau 1,5 point, +4,5 points/mois, en baisse") throw Echec("étape 6 : « " + r2.Textes[4] + " », attendu « Sceau 1,5 point, +4,5 points/mois, en baisse »");
                if (r2.Textes[2] != "Droit 60 points, en hausse") throw Echec("étape 6 : « " + r2.Textes[2] + " », attendu « Droit 60 points, en hausse »");
                if (!Phrase("Droit").Contains("Pose au pays : Prélèvement +2 %.")) throw Echec("étape 6 : la phrase du Droit ne dit pas « Pose au pays : Prélèvement +2 %. » : « " + Ligne(Phrase("Droit")) + " »");
            }
            else
            {
                for (int i = 0; i < 3; i++) if (r2.Textes[i].EndsWith(BAISSE, StringComparison.Ordinal) || r2.Textes[i].EndsWith(HAUSSE, StringComparison.Ordinal)) throw Echec("étape 6 : la jauge « " + r2.Textes[i] + " » porte un sens");
                for (int i = 3; i < 6; i++) if (!r2.Textes[i].EndsWith(HAUSSE, StringComparison.Ordinal)) throw Echec("étape 6 : la réserve « " + r2.Textes[i] + " » ne monte pas");
            }

            string cellule = depense ? "Droit" : "Plume";
            Montrer(camera, cellule, "étape 7");
            for (int i = 0; i < IMAGES; i++) yield return null;
            Juger(camera, bar, "étape 8", r1); Feuillet(camera, cellule, "étape 8");
            Tracer("barre-1-petit-seigneur", r2, "");
        }

        [ScenarioDeCapture(1032, "barre-2-royaume")]
        static IEnumerator Royaume(Camera camera)
        {
            if (cabinet == null || bar == null) throw Echec("étape 1 : le scénario barre-1-petit-seigneur n'a pas joué");
            // Le suzerain de Bar : une maison sans suzerain, qui tient plus de lieux que Bar.
            string suzerain;
            using (var client = new ClientMaison(port, TimeSpan.FromSeconds(10)))
            {
                var petit = client.LireComptes(bar); if (!petit.Presente || petit.Donnees.Suzerain == null) throw Echec("étape 1 : Bar n'a pas de suzerain : " + (petit.Absence ?? "suzerain nul"));
                suzerain = petit.Donnees.Suzerain; var haut = client.LireComptes(suzerain);
                if (!haut.Presente || haut.Donnees.Suzerain != null || haut.Donnees.Maison.Lieux.Count <= petit.Donnees.Maison.Lieux.Count)
                    throw Echec("étape 1 : le suzerain « " + suzerain + " » n'est pas un royaume : " + (haut.Absence ?? haut.Donnees.Maison.Lieux.Count + " lieux, suzerain " + (haut.Donnees.Suzerain ?? "nul")));
            }
            for (var e = Poser(suzerain, "étape 2"); e.MoveNext();) yield return null;
            long tick = cabinet.Partie.Monde.Donnees.Monde.Tick;
            Releve r1 = Juger(camera, suzerain, "étape 3, lecture R1", null);
            for (var e = Pousser(TICKS); e.MoveNext();) yield return null;
            for (var e = Prete(suzerain, tick + TICKS, "étape 4"); e.MoveNext();) yield return null;
            Releve r2 = Juger(camera, suzerain, "étape 5, lecture R2", r1);
            // Le chef des Valois a 0 en gestion : un vrai zéro, mesuré, sans sens.
            foreach (var r in new[] { r1, r2 })
                if (r.Textes[3] != "Plume 0 point, +0 point/mois") throw Echec("étape 5 : « " + r.Textes[3] + " », attendu « Plume 0 point, +0 point/mois »");
            Montrer(camera, "Plume", "étape 6");
            for (int i = 0; i < IMAGES; i++) yield return null;
            Juger(camera, suzerain, "étape 7", r1); Feuillet(camera, "Plume", "étape 7");
            Tracer("barre-2-royaume", r2, " ; maison posée par le scénario");
        }

        [ScenarioDeCapture(1032, "barre-3-sans-chef")]
        static IEnumerator SansChef(Camera camera)
        {
            if (cabinet == null) throw Echec("étape 1 : le scénario barre-1-petit-seigneur n'a pas joué");
            for (var e = Poser(SANS_CHEF, "étape 2"); e.MoveNext();) yield return null;
            Releve r = Juger(camera, SANS_CHEF, "étape 3", null);
            if (r.Pays.Nom != NOM_SANS_CHEF || r.Pays.SansChef == null) throw Echec("la maison sans chef a un chef : « " + r.Pays.Nom + " », compétences " + (r.Pays.Competences == null ? "absentes" : "servies"));
            for (int i = 3; i < 6; i++)
            {
                if (!r.Textes[i].EndsWith(", chef non connu", StringComparison.Ordinal)) throw Echec("étape 3 : « " + r.Textes[i] + " » ne finit pas par « , chef non connu »");
                if (r.Textes[i].Contains("+0") || r.Textes[i].Contains("/mois")) throw Echec("étape 3 : « " + r.Textes[i] + " » écrit un gain là où le monde n'en connaît pas");
            }
            Montrer(camera, "Plume", "étape 4");
            for (int i = 0; i < IMAGES; i++) yield return null;
            Juger(camera, SANS_CHEF, "étape 5", null); Feuillet(camera, "Plume", "étape 5");
            Tracer("barre-3-sans-chef", r, " ; maison posée par le scénario");
        }

        // Remplace la lecture du cabinet par une lecture faite des clients de `LecturePartie.Locale`, dont le monde nomme la maison donnée : le service,
        // `/pays`, son tick et la barre sont les vrais ; seule la maison du joueur est posée ici.
        static IEnumerator Poser(string maison, string quand)
        {
            Infobulle.Cacher(toile.GetComponent<Canvas>());
            for (var e = Lot690.Jusqua(() => !cabinet.Partie.Occupee, () => quand + " : partie " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            cabinet.Partie = Posee(maison);
            for (var e = Prete(maison, null, quand); e.MoveNext();) yield return null;
        }

        static LecturePartie Posee(string maison)
        {
            int p = port; var delai = TimeSpan.FromSeconds(10);
            return new LecturePartie(
                () => { using (var c = new ClientMonde(p, delai)) { var l = c.LireAvecMaison(); return l.Presente ? Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(l.Donnees.Monde, maison)) : l; } },
                id => { using (var c = new ClientMaison(p, delai)) return c.Lire(id); },
                () => { using (var c = new ClientDeparts(p, ClientDeparts.DelaiMinimal)) return c.Lire(); },
                id => RecuIntention.Absente("maison posée par le scénario"),
                id => { using (var c = new ClientMaison(p, delai)) return c.LireComptes(id); },
                id => { using (var c = new ClientPays(p, delai)) return c.Lire(id); });
        }

        static IEnumerator Pousser(int n)
        {
            var poussee = Task.Run(() => { for (int i = 0; i < n; i++) { var r = Lot690.PousserTick(port).Result; if (r.statut != 200) return r; } return (200, ""); });
            for (var e = Lot690.Attendre(poussee, n + " tick(s)"); e.MoveNext();) yield return null;
            if (poussee.Result.Item1 != 200) throw Echec("tick " + poussee.Result.Item2);
        }

        // La barre de `maison` (n'importe laquelle si nulle) a lu le monde et le pays du même tick (`tick`, n'importe lequel si nul), et ses six cellules sont actives.
        static bool Pret(string maison, long? tick)
        {
            var p = cabinet.Partie; var m = p.Monde; var y = p.Pays;
            if (p.Occupee || m == null || !m.Presente || m.Donnees.MaisonDuJoueur == null) return false;
            if (maison != null && m.Donnees.MaisonDuJoueur != maison || tick != null && m.Donnees.Monde.Tick != tick) return false;
            if (y == null || !y.Presente || y.Donnees.MaisonId != m.Donnees.MaisonDuJoueur || y.Donnees.Tick != m.Donnees.Monde.Tick) return false;
            return conteneur.gameObject.activeInHierarchy && CELLULES.All(n => { var t = conteneur.Find(n); return t != null && t.gameObject.activeInHierarchy; });
        }

        static string Dire() => "partie " + Lot690.Dire(cabinet.Partie) + ", pays " + (cabinet.Partie.Pays == null ? "non lu" : !cabinet.Partie.Pays.Presente ? "absent : " + cabinet.Partie.Pays.Absence : "au tick " + N(cabinet.Partie.Pays.Donnees.Tick));

        // Attend que la barre soit prête, laisse passer une image pour qu'elle se redessine, et exige qu'elle le soit encore.
        static IEnumerator Prete(string maison, long? tick, string quand)
        {
            for (var e = Lot690.Jusqua(() => Pret(maison, tick), () => quand + " : " + Dire()); e.MoveNext();) yield return null;
            yield return null;
            for (var e = Lot690.Jusqua(() => Pret(maison, tick), () => quand + " : " + Dire()); e.MoveNext();) yield return null;
        }

        static Text Cellule(string nom) => conteneur.Find(nom)?.GetComponent<Text>() ?? throw Echec("cellule « " + nom + " » introuvable");
        static Infobulle Bulle(string nom) { var t = Cellule(nom); return t.GetComponent<Infobulle>() ?? t.GetComponentInChildren<Infobulle>(true) ?? throw Echec("cellule « " + nom + " » sans infobulle"); }
        static string Phrase(string nom) => Bulle(nom).Phrase ?? throw Echec("cellule « " + nom + " » : infobulle sans phrase");

        // Relit `/pays` à part et juge la barre contre lui, dans la même image : la première faute lève l'erreur. `avant` est la lecture d'avant de la même maison
        // (nulle pour la première) : le sens attendu d'une cellule est le signe de sa valeur servie moins celle de `avant`.
        static Releve Juger(Camera camera, string id, string quand, Releve avant)
        {
            Lecture<PaysLu> lu; using (var client = new ClientPays(port, TimeSpan.FromSeconds(10))) lu = client.Lire(id);
            if (!lu.Presente) throw Echec(quand + " : pays de « " + id + " » absent : " + lu.Absence);
            PaysLu p = lu.Donnees; var lue = cabinet.Partie.Pays; long? tickLu = lue != null && lue.Presente ? (long?)lue.Donnees.Tick : null;
            if (tickLu != (long)p.Tick) throw Echec(quand + " : barre lue au tick " + N(tickLu) + ", pays servi au tick " + N(p.Tick));
            if (!conteneur.gameObject.activeInHierarchy) throw Echec(quand + " : « " + CONTENEUR + " » est caché");
            foreach (var autre in conteneur.GetComponentsInChildren<Text>(true).Where(x => !CELLULES.Contains(x.name)))
                if (autre.gameObject.activeInHierarchy) throw Echec(quand + " : le texte d'état « " + autre.text + " » reste actif");

            var r = new Releve { Pays = p }; string date = TexteDuMonde.Date(p.Date);
            for (int i = 0; i < CLES.Length; i++)
            {
                string cle = CLES[i], nom = CELLULES[i], texte, debut; string[] exiges; double valeur;
                if (i < 3)
                {
                    if (!p.Jauges.TryGetValue(cle, out var j)) throw Echec(quand + " : jauge « " + cle + " » non servie");
                    valeur = j.Valeur; texte = j.Nom + " " + Pts(valeur);
                    debut = j.Nom + " : " + j.Dit + ". " + Pts(valeur) + ", de " + Pts(j.Minimum) + " à " + Pts(j.Maximum) + ", neutre à " + Pts(j.Neutre) + ".";
                    var poses = p.Poses.Where(x => x.Jauge == cle).Select(x => "Pose au pays : " + x.NomDeLaGrandeur + " " + Signe(x.Valeur * 100) + " %.").ToArray();
                    exiges = poses.Length > 0 ? poses : new[] { "À son neutre, elle ne pose rien." };
                }
                else
                {
                    if (!p.Points.TryGetValue(cle, out var q)) throw Echec(quand + " : réserve « " + cle + " » non servie");
                    valeur = q.Valeur;
                    debut = q.Nom + " : " + q.Dit + ". " + Pts(valeur) + ", au plus " + Pts(q.Plafond) + ".";
                    if (p.Competences == null)
                    {
                        if (q.ParMois != null) throw Echec(quand + " : « " + q.Nom + " » : un gain servi pour un chef que le monde ne connaît pas");
                        texte = q.Nom + " " + Pts(valeur) + ", chef non connu"; exiges = new[] { "absent, pas nul" };
                    }
                    else
                    {
                        double parMois = q.ParMois ?? throw Echec(quand + " : « " + q.Nom + " » : chef connu, gain par mois absent");
                        texte = q.Nom + " " + Pts(valeur) + ", +" + Pts(parMois) + "/mois";
                        exiges = new[] { "Gagne " + Pts(parMois) + " par mois : la " + q.Domaine + " du chef, " + Pts(p.Competences[q.Domaine]) + "." };
                    }
                }
                r.Valeurs[nom] = valeur;
                double precedente = 0; string sens = "";
                if (avant != null && avant.Valeurs.TryGetValue(nom, out precedente) && precedente != valeur) sens = valeur < precedente ? BAISSE : HAUSSE;
                if (sens != "")
                {
                    string mot = sens == BAISSE ? "En baisse" : "En hausse";
                    exiges = exiges.Concat(new[] { mot + " depuis le ", " : de " + Pts(precedente) + " à " + Pts(valeur) + "." }).ToArray();
                }
                texte += sens; r.Textes[i] = texte;

                Text cellule = Cellule(nom);
                if (!cellule.isActiveAndEnabled) throw Echec(quand + " : cellule « " + nom + " » inactive");
                if (cellule.text != texte) throw Echec(quand + " : cellule « " + nom + " » « " + cellule.text + " » ≠ attendu « " + texte + " »");
                string phrase = Phrase(nom);
                if (!phrase.StartsWith(debut, StringComparison.Ordinal)) throw Echec(quand + " : phrase de « " + nom + " » « " + Ligne(phrase) + " » ne commence pas par « " + debut + " »");
                if (!phrase.EndsWith("Relevé au " + date + ".", StringComparison.Ordinal)) throw Echec(quand + " : phrase de « " + nom + " » « " + Ligne(phrase) + " » ne finit pas par « Relevé au " + date + ". »");
                foreach (string exige in exiges) if (!phrase.Contains(exige)) throw Echec(quand + " : phrase de « " + nom + " » « " + Ligne(phrase) + " » sans « " + exige + " »");
                foreach (string ecrit in new[] { texte, phrase })
                    if ((TexteDuMonde.Interdit(ecrit, id) ?? TexteDuMonde.SansUnite(ecrit)) is string refuse) throw Echec(quand + " : « " + refuse + " » refusé dans « " + Ligne(ecrit) + " »");
                if (cellule.preferredWidth > cellule.rectTransform.rect.width + 0.5f || cellule.preferredHeight > cellule.rectTransform.rect.height + 0.5f)
                    throw Echec(quand + " : cellule « " + nom + " » coupée : " + cellule.preferredWidth + " × " + cellule.preferredHeight + " pour " + cellule.rectTransform.rect.width + " × " + cellule.rectTransform.rect.height);
                Lot690.DansLeChamp(camera, cellule);
            }
            return r;
        }

        static Rect Ecran(Camera camera, RectTransform cadre)
        {
            var coins = new Vector3[4]; cadre.GetWorldCorners(coins); var p = coins.Select(c => camera.WorldToScreenPoint(c)).ToArray();
            return Rect.MinMaxRect(p.Min(v => v.x), p.Min(v => v.y), p.Max(v => v.x), p.Max(v => v.y));
        }

        // L'infobulle de la cellule, au centre de la cellule : ouverte pour la photo.
        static void Montrer(Camera camera, string nom, string quand)
        {
            string phrase = Phrase(nom);
            Infobulle.Montrer(toile.GetComponent<Canvas>(), phrase, Ecran(camera, (RectTransform)Cellule(nom).transform).center);
            Feuillet(camera, nom, quand);
        }

        // Le feuillet est actif, dit la phrase de la cellule, et tient entier dans l'image.
        static void Feuillet(Camera camera, string nom, string quand)
        {
            var feuillet = toile.Find("Infobulle") as RectTransform; string phrase = Phrase(nom);
            var ecrit = feuillet != null ? feuillet.GetComponentInChildren<Text>(true) : null;
            if (feuillet == null || !feuillet.gameObject.activeInHierarchy || ecrit == null || ecrit.text != phrase)
                throw Echec(quand + " : infobulle de « " + nom + " » absente ou changée : « " + Ligne(ecrit?.text) + " »");
            Rect cadre = Ecran(camera, feuillet), image = new Rect(0, 0, camera.pixelWidth, camera.pixelHeight);
            if (cadre.xMin < -0.5f || cadre.yMin < -0.5f || cadre.xMax > image.xMax + 0.5f || cadre.yMax > image.yMax + 0.5f)
                throw Echec(quand + " : infobulle de « " + nom + " » hors de l'image : " + cadre + " dans " + image);
        }

        static void Tracer(string scenario, Releve r, string ajout) =>
            Debug.Log("CAPTURE_1032 " + scenario + " maison « " + r.Pays.Nom + " » au tick " + N(cabinet.Partie.Pays.Donnees.Tick) + ", pays servi au tick " + N(r.Pays.Tick)
                + " : " + string.Join(" | ", r.Textes) + ajout);
    }
}
