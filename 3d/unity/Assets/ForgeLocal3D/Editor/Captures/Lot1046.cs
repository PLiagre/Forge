using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 1046 : le panneau « Gestes des jauges », à droite du feuillet « Le pays », dit prix, effet et refus de chaque geste, dépose `depenser_jauge` par le chemin
    // des intentions, et montre le refus du service. Deux scénarios, joués dans l'ordre de leur nom, sur le même service et la même partie :
    //   1. Bar-le-Duc choisi, le feuillet ouvert, « Asseoir le droit » payé (reçu), puis déposé une seconde fois le même jour : le monde le refuse ;
    //   2. le jour suivant : le Droit payé est là, la barre le montre, et « Asseoir le droit » se refuse d'avance, avant tout clic.
    // Le texte attendu de chaque geste s'écrit ici, d'après le format du brief, depuis la lecture `new ClientPays(port, …).LireGestes(bar)` : ni `GestesDesJauges.Geste`
    // ni `Raison` ne sont appelés. Contre-épreuve : `-forge1046Avance` pousse un tick entre le geste payé et le second : le panneau refuse d'avance, le refus du service
    // n'est jamais atteint, et le scénario échoue (« le panneau refuse d'avance : … »).
    static class Lot1046
    {
        const string AVANCE = "-forge1046Avance", TICKS_ARG = "-forgeTicks", SIEGE = "Bar-le-Duc", BANDEAU = "FORGE · Le cabinet";
        const string ASSEOIR = "asseoir_le_droit", AFFERMIR = "affermir_la_concorde";
        const double COUT_DU_DROIT = 30, GAIN_DU_DROIT = 10;
        const int IMAGES = 10;
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        static CarteDessinee carte;
        static CabinetDeCarte cabinet;
        static GestesDesJauges panneau;
        static Transform toile;
        static RectTransform cadre;
        static Button icone;
        static int port, acceptes, refuses;
        static string bar;
        // Le pays servi au jugement R1 du premier scénario : le deuxième le relit un jour plus tard.
        static double sceauR1, droitR1;

        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string N(long? v) => v == null ? "non servi" : v.Value.ToString(Inv);
        static string Ligne(string t) => t == null ? "(aucun)" : t.Replace("\r", "").Replace("\n", " | ");
        static bool Drapeau(string nom) => Environment.GetCommandLineArgs().Contains(nom);
        static string P(double v) => TexteDuMonde.Points(v);
        // Le participe s'accorde comme les points : un seul sous deux, au dixième.
        static string Accord(double v, string mot) => Math.Abs(Math.Round(v, 1, MidpointRounding.AwayFromZero)) < 2 ? mot : mot + "s";

        // Le parcours part du tick demandé au service : `-forgeTicks`, sinon le défaut de `ForgeCapture` (30), comme `Lot1045`.
        static long Depart()
        {
            var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, TICKS_ARG);
            return i >= 0 && i + 1 < a.Length ? long.Parse(a[i + 1], Inv) : 30;
        }

        [ScenarioDeCapture(1046, "gestes-1-paye-puis-refuse")]
        static IEnumerator PayePuisRefuse(Camera camera)
        {
            acceptes = refuses = 0;
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null; // étape 1
            carte = ouverte.Carte; port = carte.port;
            cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : pas de CabinetDeCarte");
            panneau = carte.GetComponent<GestesDesJauges>() ?? throw Echec("étape 1 : pas de GestesDesJauges sur la carte");
            toile = carte.transform.Find("Cabinet") ?? throw Echec("étape 1 : pas de toile du cabinet");
            cadre = (RectTransform)toile.Find(DossierPays.TITRE) ?? throw Echec("étape 1 : feuillet « " + DossierPays.TITRE + " » introuvable");
            icone = toile.Find(BANDEAU + "/" + CabinetDeCarte.PAYS + "/" + DossierPays.ICONE)?.GetComponent<Button>() ?? throw Echec("étape 1 : icône « " + DossierPays.ICONE + " » introuvable dans le bandeau");
            if (panneau.Panneau.parent != cadre) throw Echec("étape 1 : le panneau « " + GestesDesJauges.TITRE + " » n'est pas dans le cadre du feuillet");
            if (cadre.gameObject.activeSelf || panneau.Panneau.gameObject.activeInHierarchy) throw Echec("étape 1 : le feuillet ou le panneau est ouvert d'avance");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 2 : partie " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null; // étape 2
            // La toile sur la caméra de la photo, comme `Lot1045` : les jugements de cadre se font sur ce que l'image montre.
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
            for (var e = Lot690.Jusqua(() => Lue(tick + 1), () => "étape 3 : " + Dire()); e.MoveNext();) yield return null;
            bar = cabinet.Partie.Monde.Donnees.MaisonDuJoueur; tick++;

            icone.onClick.Invoke();
            if (!cadre.gameObject.activeSelf) throw Echec("étape 4 : le clic sur l'icône « " + DossierPays.ICONE + " » n'ouvre pas le feuillet");
            if (!panneau.Panneau.gameObject.activeInHierarchy) throw Echec("étape 4 : le panneau « " + GestesDesJauges.TITRE + " » ne s'ouvre pas avec le feuillet");
            for (var e = Prete(tick, "étape 4"); e.MoveNext();) yield return null;

            // Jugement R1, dans une seule image.
            GestesDuPays r1 = Juger(camera, "étape 5, jugement R1");
            sceauR1 = r1.Pays.Points["sceau"].Valeur; droitR1 = r1.Pays.Jauges["droit"].Valeur;
            var droitServi = r1.Gestes.Single(g => g.Id == ASSEOIR);
            if (sceauR1 < COUT_DU_DROIT || droitServi.Refus != null) throw Echec("Bar ne peut pas asseoir son droit : Sceau " + P(sceauR1) + ", refus servi « " + (droitServi.Refus ?? "nul") + " »");

            // Le geste payé : « Asseoir le droit », choisi puis confirmé ; le monde le paiera au jour suivant.
            panneau.BoutonDuGeste(ASSEOIR).onClick.Invoke();
            yield return null;
            if (panneau.Ordre.Brouillon == null) throw Echec("étape 6 : le clic sur « Asseoir le droit » ne prépare aucun geste");
            if (!panneau.BoutonConfirmer.gameObject.activeSelf || !panneau.BoutonConfirmer.interactable) throw Echec("étape 6 : « " + GestesDesJauges.CONFIRMER + " » n'est pas offert");
            panneau.BoutonConfirmer.onClick.Invoke();
            for (var e = Lot690.Jusqua(() => panneau.Ordre.Recu != null, () => "étape 6 : aucun reçu du geste payé"); e.MoveNext();) yield return null;
            yield return null;
            var recu = panneau.Ordre.Recu;
            if (!recu.Acceptee) throw Echec("étape 6 : le geste payé est refusé : " + (recu.Presente ? recu.Erreur : recu.Absence));
            if (recu.AppliqueeAuTick != tick) throw Echec("étape 6 : reçu au tick " + N(recu.AppliqueeAuTick) + ", monde lu au tick " + N(tick));
            if (!panneau.MessageAffiche.StartsWith("Asseoir le droit : geste reçu au ", StringComparison.Ordinal)) throw Echec("étape 6 : message « " + Ligne(panneau.MessageAffiche) + " »");
            acceptes++;

            // Le geste refusé : le même jour, le monde compte le premier geste ; /pays, lui, ne le compte pas.
            panneau.BoutonRetour.onClick.Invoke();
            yield return null;
            if (Drapeau(AVANCE))
            {
                for (var e = Pousser(1); e.MoveNext();) yield return null;
                tick++;
                for (var e = Prete(tick, "étape 7, un tick plus tard"); e.MoveNext();) yield return null;
            }
            var bouton = panneau.BoutonDuGeste(ASSEOIR) ?? throw Echec("étape 7 : le bouton « Asseoir le droit » a disparu");
            if (!bouton.interactable) throw Echec("le panneau refuse d'avance : " + LigneQuatre(panneau.TexteDuGeste(ASSEOIR)));
            bouton.onClick.Invoke();
            yield return null;
            if (panneau.Ordre.Brouillon == null) throw Echec("étape 7 : le second clic sur « Asseoir le droit » ne prépare aucun geste");
            panneau.BoutonConfirmer.onClick.Invoke();
            for (var e = Lot690.Jusqua(() => panneau.Ordre.Recu != null, () => "étape 7 : aucun reçu du second geste"); e.MoveNext();) yield return null;
            yield return null;
            recu = panneau.Ordre.Recu;
            if (recu.Acceptee) throw Echec("étape 7 : le second geste du même jour est accepté au tick " + N(recu.AppliqueeAuTick));
            if (!recu.Presente) throw Echec("étape 7 : reçu du second geste absent : " + recu.Absence);
            if (recu.Statut != 400) throw Echec("étape 7 : statut " + N(recu.Statut) + " au lieu de 400 : " + recu.Erreur);
            if (cabinet.Partie.Monde.Donnees.Monde.Tick != depart + 1) throw Echec("étape 7 : le monde est au tick " + N(cabinet.Partie.Monde.Donnees.Monde.Tick) + ", un seul tick (" + N(depart + 1) + ") devait avoir passé");
            double reste = Servi().Pays.Points["sceau"].Valeur - COUT_DU_DROIT;
            string attendu = "× Demande refusée\nAsseoir le droit : pas assez de points de Sceau : " + P(COUT_DU_DROIT) + " " + Accord(COUT_DU_DROIT, "demandé") + ", " + P(reste) + " " + Accord(reste, "disponible");
            if (panneau.MessageAffiche != attendu) throw Echec("étape 7 : message « " + Ligne(panneau.MessageAffiche) + " », attendu « " + Ligne(attendu) + " »");
            Couleur("étape 7", SocleInterface.Couleur("alerte"));
            refuses++;
            for (int i = 0; i < IMAGES; i++) yield return null;
            if (panneau.MessageAffiche != attendu) throw Echec("étape 8 : le message a changé : « " + Ligne(panneau.MessageAffiche) + " »");
            Tracer("gestes-1-paye-puis-refuse", Servi());
        }

        [ScenarioDeCapture(1046, "gestes-2-jour-suivant")]
        static IEnumerator JourSuivant(Camera camera)
        {
            if (cabinet == null || bar == null) throw Echec("étape 1 : le scénario gestes-1-paye-puis-refuse n'a pas joué");
            long tick = cabinet.Partie.Monde.Donnees.Monde.Tick;
            // Le refus du premier scénario se referme : si le bouton reste éteint, c'est le refus servi qui l'éteint, non un reçu qui attend.
            panneau.BoutonRetour.onClick.Invoke();
            yield return null;
            for (var e = Pousser(1); e.MoveNext();) yield return null;
            tick++;
            for (var e = Prete(tick, "étape 2"); e.MoveNext();) yield return null;

            GestesDuPays servi = Juger(camera, "étape 3, jugement");
            // Le même monde : le Sceau payé a manqué, le Droit est monté, un seul geste a été payé et le refus n'a rien pris.
            double sceau = servi.Pays.Points["sceau"].Valeur, droit = servi.Pays.Jauges["droit"].Valeur;
            if (Math.Abs(sceau - (sceauR1 - COUT_DU_DROIT)) > 1e-9) throw Echec("étape 3 : Sceau " + P(sceau) + ", attendu " + P(sceauR1 - COUT_DU_DROIT) + " (" + P(sceauR1) + " moins " + P(COUT_DU_DROIT) + ")");
            if (Math.Abs(droit - (droitR1 + GAIN_DU_DROIT)) > 1e-9) throw Echec("étape 3 : Droit " + P(droit) + ", attendu " + P(droitR1 + GAIN_DU_DROIT) + " (" + P(droitR1) + " plus " + P(GAIN_DU_DROIT) + ")");
            // Le refus d'avance, avant tout clic.
            var asseoir = servi.Gestes.SingleOrDefault(g => g.Id == ASSEOIR) ?? throw Echec("étape 3 : le geste « " + ASSEOIR + " » n'est pas servi");
            const string DEBUT = "pas assez de points de Sceau : 30 points demandés, ";
            if (asseoir.Refus == null || !asseoir.Refus.StartsWith(DEBUT, StringComparison.Ordinal)) throw Echec("étape 3 : refus servi « " + (asseoir.Refus ?? "nul") + " », attendu un refus qui commence par « " + DEBUT + " »");
            string ligne = LigneQuatre(panneau.TexteDuGeste(ASSEOIR));
            if (ligne != "Refusé d'avance : " + asseoir.Refus) throw Echec("étape 3 : ligne 4 « " + ligne + " », attendue « Refusé d'avance : " + asseoir.Refus + " »");
            if (panneau.BoutonDuGeste(ASSEOIR).interactable) throw Echec("étape 3 : le bouton « Asseoir le droit » est actif malgré le refus servi");
            if (panneau.Ordre.Brouillon != null || panneau.Ordre.Recu != null) throw Echec("étape 3 : un geste ou un reçu attend encore dans le panneau");
            // La barre montre le Droit payé, en hausse, et le Sceau qui manque.
            string cleDroit = "Droit " + P(droit) + ", en hausse", debutSceau = "Sceau " + P(sceau);
            for (var e = Lot690.Jusqua(() => Cellule("Droit").text == cleDroit && Cellule("Sceau").text.StartsWith(debutSceau, StringComparison.Ordinal),
                () => "étape 3 : la barre dit « " + Cellule("Droit").text + " » et « " + Cellule("Sceau").text + " », attendu « " + cleDroit + " » et « " + debutSceau + "… »"); e.MoveNext();) yield return null;
            for (int i = 0; i < IMAGES; i++) yield return null;
            Juger(camera, "étape 4");
            Tracer("gestes-2-jour-suivant", Servi());
        }

        static IEnumerator Pousser(int n)
        {
            var poussee = Task.Run(() => { for (int i = 0; i < n; i++) { var r = Lot690.PousserTick(port).Result; if (r.statut != 200) return r; } return (200, ""); });
            for (var e = Lot690.Attendre(poussee, n + " tick(s)"); e.MoveNext();) yield return null;
            if (poussee.Result.Item1 != 200) throw Echec("tick " + poussee.Result.Item2);
        }

        // La partie est libre et a lu le monde, au tick donné (n'importe lequel si nul), et les gestes de la maison du joueur au même tick.
        static bool Lue(long? tick)
        {
            var p = cabinet.Partie; var m = p.Monde; var g = p.Gestes;
            if (p.Occupee || m == null || !m.Presente || m.Donnees.MaisonDuJoueur == null) return false;
            if (bar != null && m.Donnees.MaisonDuJoueur != bar || tick != null && m.Donnees.Monde.Tick != tick) return false;
            return g != null && g.Presente && g.Donnees.MaisonId == m.Donnees.MaisonDuJoueur && g.Donnees.Tick == m.Donnees.Monde.Tick;
        }

        static string Dire() => "partie " + Lot690.Dire(cabinet.Partie) + ", gestes " + (cabinet.Partie.Gestes == null ? "non lus" : !cabinet.Partie.Gestes.Presente ? "absents : " + cabinet.Partie.Gestes.Absence : "au tick " + N(cabinet.Partie.Gestes.Donnees.Tick));

        // Attend la partie au tick, puis le panneau qui écrit les deux gestes, laisse passer une image et exige qu'il les écrive encore.
        static IEnumerator Prete(long tick, string quand)
        {
            bool Ecrit() => Lue(tick) && !string.IsNullOrEmpty(panneau.TexteDuGeste(ASSEOIR)) && !string.IsNullOrEmpty(panneau.TexteDuGeste(AFFERMIR));
            for (var e = Lot690.Jusqua(Ecrit, () => quand + " : " + Dire() + ", état « " + Ligne(panneau.EtatAffiche) + " »"); e.MoveNext();) yield return null;
            yield return null;
            for (var e = Lot690.Jusqua(Ecrit, () => quand + " : " + Dire() + ", état « " + Ligne(panneau.EtatAffiche) + " »"); e.MoveNext();) yield return null;
        }

        static GestesDuPays Servi()
        {
            Lecture<GestesDuPays> lu;
            using (var client = new ClientPays(port, TimeSpan.FromSeconds(10))) lu = client.LireGestes(bar);
            if (!lu.Presente) throw Echec("gestes de « " + bar + " » absents : " + lu.Absence);
            return lu.Donnees;
        }

        // Le texte d'un geste, d'après le format du brief ; les noms et les valeurs sont ceux de la lecture, jamais un identifiant.
        static string Attendu(GestesDuPays s, GesteLu g)
        {
            string Prix(string cle, double v) => P(v) + " de " + s.Pays.Points[cle].Nom + " (en réserve : " + P(s.Pays.Points[cle].Valeur) + ")";
            string Effet(string cle, double v) => (v > 0 ? "+" : "") + P(v) + " de " + s.Pays.Jauges[cle].Nom + " (aujourd'hui : " + P(s.Pays.Jauges[cle].Valeur) + ")";
            return g.Nom + "\nPrix : " + string.Join(" et ", g.Cout.Select(c => Prix(c.Key, c.Value))) + "\nEffet : " + string.Join(" et ", g.Effet.Select(c => Effet(c.Key, c.Value)))
                + "\n" + (g.Refus == null ? "Payable aujourd'hui" : "Refusé d'avance : " + g.Refus);
        }

        static string LigneQuatre(string texte)
        {
            var lignes = (texte ?? "").Split('\n');
            return lignes.Length >= 4 ? lignes[3] : "(texte du geste à " + lignes.Length + " ligne(s) : « " + Ligne(texte) + " »)";
        }

        static Text Cellule(string nom) => toile.Find(BANDEAU + "/" + BarreDuPays.NOM + "/" + nom)?.GetComponent<Text>() ?? throw Echec("cellule « " + nom + " » de la barre introuvable");

        static void Couleur(string quand, Color attendue)
        {
            var message = panneau.Panneau.GetComponentsInChildren<Text>(true).Single(t => t.name == "Message des gestes");
            if (message.color != attendue) throw Echec(quand + " : le message est en " + message.color + ", attendu " + attendue);
        }

        // Relit `/pays` et juge le panneau contre lui, dans la même image et sans `yield` : la première faute lève l'erreur.
        static GestesDuPays Juger(Camera camera, string quand)
        {
            var servi = Servi(); var partie = cabinet.Partie; var lus = partie.Gestes;
            long? tickLu = lus != null && lus.Presente ? (long?)lus.Donnees.Tick : null;
            if (tickLu != servi.Tick) throw Echec(quand + " : panneau lu au tick " + N(tickLu) + ", gestes servis au tick " + N(servi.Tick));
            long tickDuMonde = partie.Monde.Donnees.Monde.Tick;
            if (tickLu != tickDuMonde) throw Echec(quand + " : panneau lu au tick " + N(tickLu) + ", monde lu au tick " + N(tickDuMonde));
            if (lus.Donnees.MaisonId != bar) throw Echec(quand + " : panneau lu pour « " + lus.Donnees.MaisonId + " », maison du joueur « " + bar + " »");
            if (servi.Gestes.Count != 2 || servi.Gestes.All(g => g.Id != ASSEOIR)) throw Echec(quand + " : " + servi.Gestes.Count + " gestes servis, deux attendus dont « " + ASSEOIR + " »");
            string etat = servi.Pays.Nom + " · relevé au " + TexteDuMonde.Date(servi.Pays.Date);
            if (panneau.EtatAffiche != etat) throw Echec(quand + " : état « " + Ligne(panneau.EtatAffiche) + " », attendu « " + etat + " »");
            foreach (var g in servi.Gestes)
            {
                string[] a = Attendu(servi, g).Split('\n'), e = (panneau.TexteDuGeste(g.Id) ?? "").Split('\n');
                for (int i = 0; i < Math.Max(a.Length, e.Length); i++)
                    if (i >= a.Length || i >= e.Length || a[i] != e[i])
                        throw Echec(quand + " : geste « " + g.Nom + " », ligne " + (i + 1) + " : attendue « " + (i < a.Length ? a[i] : "(aucune)") + " », lue « " + (i < e.Length ? e[i] : "(aucune)") + " »");
                var bouton = panneau.BoutonDuGeste(g.Id) ?? throw Echec(quand + " : pas de bouton pour « " + g.Nom + " »");
                bool libre = panneau.Ordre.Brouillon == null && panneau.Ordre.Recu == null && !panneau.Ordre.EnCours;
                if (bouton.interactable != (libre && g.Refus == null)) throw Echec(quand + " : le bouton « " + g.Nom + " » est " + (bouton.interactable ? "actif" : "éteint") + ", refus servi « " + (g.Refus ?? "nul") + " »" + (libre ? "" : ", un geste attend"));
            }
            foreach (var t in panneau.Panneau.GetComponentsInChildren<Text>())
                if ((TexteDuMonde.Interdit(t.text, bar) ?? TexteDuMonde.SansUnite(t.text)) is string refuse) throw Echec(quand + " : « " + refuse + " » refusé dans le texte « " + Ligne(t.text) + " » du panneau");

            if (!cadre.gameObject.activeInHierarchy || !panneau.Panneau.gameObject.activeInHierarchy) throw Echec(quand + " : le feuillet ou le panneau « " + GestesDesJauges.TITRE + " » n'est pas actif");
            var coins = new Vector3[4]; panneau.Panneau.GetWorldCorners(coins);
            for (int i = 0; i < 4; i++)
            {
                Vector3 v = camera.WorldToViewportPoint(coins[i]);
                if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) throw Echec(quand + " : coin " + i + " du panneau hors de l'image : " + v.ToString("F3"));
            }
            Lot690.DansLeChamp(camera, panneau.Panneau.GetComponentsInChildren<Text>().First(t => t.name == GestesDesJauges.TITRE));
            Lot690.DansLeChamp(camera, panneau.Panneau.GetComponentsInChildren<Text>(true).Single(t => t.name == "Message des gestes"));
            return servi;
        }

        static void Tracer(string scenario, GestesDuPays s)
        {
            double Valeur(string cle) => s.Pays.Points.TryGetValue(cle, out var r) ? r.Valeur : s.Pays.Jauges[cle].Valeur;
            Debug.Log("CAPTURE_1046 " + scenario + " " + s.Pays.Nom + " au tick " + N(s.Tick) + " : Sceau " + P(Valeur("sceau")) + ", Droit " + P(Valeur("droit")) + ", Plume " + P(Valeur("plume"))
                + ", reçus " + acceptes.ToString(Inv) + "/" + refuses.ToString(Inv) + ", message « " + Ligne(panneau.MessageAffiche) + " »");
        }
    }
}
