using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 655 : Mistra choisi dans le cabinet, le feuillet « Terres et comptes » ouvert par son bouton, la part fixée à 25 %, trente
    // jours poussés ; le feuillet se relit seul au tick publié. `-forge655SansTick` omet seulement le POST /tick?n=30 : il rougit.
    static class Lot655
    {
        const string SIEGE = "Mistra", TERRE = "Despotat de Morée", FEUILLET = "Terres et comptes", SANS_TICK = "-forge655SansTick";
        const double ATTENTE_S = 30, ATTENTE_RELECTURE_S = 15;
        const int JOURS = 30, IMAGES_DE_POSE = 10;
        internal static DossierMaison Dossier; internal static Text Texte; internal static ComptesDeMaison ComptesLus; internal static int Port;
        static readonly CultureInfo Fr = CultureInfo.GetCultureInfo("fr-FR");
        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);
        static string Ligne(string texte) => texte == null ? "(aucun texte)" : texte.Replace("\r", "").Replace("\n", " | ");
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        // Le feuillet dit cette date servie et cette part, chacune sur sa ligne.
        static bool Dit(string texte, DateDuMonde date, string part) => texte != null && texte.Contains(" · " + TexteDuMonde.Date(date) + Environment.NewLine)
            && texte.Contains("Prélèvement : " + part + " %" + Environment.NewLine);

        [ScenarioDeCapture(655, "mistra-terres-et-comptes")]
        internal static IEnumerator MistraTerresEtComptes(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            CarteDessinee carte = ouverte.Carte; int port = carte.port;
            CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("la carte n'a pas de CabinetDeCarte");
            DossierMaison[] dossiers = carte.GetComponentsInChildren<DossierMaison>(true);
            if (dossiers.Length != 1) throw Echec("attendu exactement 1 DossierMaison sur la carte, observé " + dossiers.Length);
            DossierMaison dossier = dossiers[0];
            Transform toile = carte.transform.Find("Cabinet");
            if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("la toile du cabinet n'est pas active");
            HorlogeDeCarte horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Echec("la carte n'a pas d'horloge");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            for (var e = Lot690.Jusqua(() => horloge.Lue != null, () => "horloge jamais activée : " + (horloge.Absence ?? horloge.TexteAffiche)); e.MoveNext();) yield return null;
            if (horloge.Lue.JoursParSeconde != 0) throw Echec("service hors pause : " + horloge.Lue.JoursParSeconde + " jour(s) par seconde");

            LecturePartie partie = cabinet.Partie;
            FicheDeDepart[] mistra = partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (mistra.Length != 1 || mistra[0].Nom != TERRE) throw Echec("fiches au siège " + SIEGE + " : " + string.Join(", ", mistra.Select(f => f.Nom)) + ", attendu « " + TERRE + " » seule");
            FicheDeDepart fiche = mistra[0]; long tick = partie.Monde.Donnees.Monde.Tick;
            Task choix = partie.Choisir(fiche.Id);
            for (var e = Lot690.Attendre(choix, "choix de " + fiche.Nom); e.MoveNext();) yield return null;
            RecuIntention recu = partie.Recu;
            if (recu == null || !recu.Acceptee || recu.AppliqueeAuTick != tick) throw Echec("reçu du choix : " + (recu == null ? "aucun" : recu.Acceptee ? "tick " + recu.AppliqueeAuTick + ", attendu " + N(tick) : recu.Presente ? recu.Erreur : recu.Absence));
            var un = Pousser(port, 1);
            for (var e = Lot690.Attendre(un, "POST /tick?n=1"); e.MoveNext();) yield return null;
            if (un.Result.statut != 200) throw Echec("POST /tick?n=1 a rendu " + un.Result.statut + " : " + un.Result.corps);
            for (var e = Lot690.Jusqua(() => { var p = cabinet.Partie; return !p.Occupee && p.Monde?.Presente == true && p.Monde.Donnees.Monde.Tick == tick + 1 && p.Monde.Donnees.MaisonDuJoueur != null
                && p.Maison?.Presente == true && p.Maison.Donnees.Id == p.Monde.Donnees.MaisonDuJoueur; }, () => "le cabinet n'a pas lu la maison du joueur : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            string maison = partie.Monde.Donnees.MaisonDuJoueur;
            if (partie.Maison.Donnees.Siege.Nom != SIEGE) throw Echec("maison " + maison + " au siège « " + partie.Maison.Donnees.Siege.Nom + " », attendu " + SIEGE);

            // Le geste du joueur : le bouton du cabinet ouvre le feuillet.
            Button[] boutons = toile.GetComponentsInChildren<Button>(true).Where(b => b.name == FEUILLET).ToArray();
            if (boutons.Length != 1 || !boutons[0].gameObject.activeInHierarchy || !boutons[0].interactable) throw Echec("bouton « " + FEUILLET + " » : " + boutons.Length + " trouvé(s), attendu 1 actif");
            boutons[0].onClick.Invoke();
            var coutume = Comptes(port, maison);
            for (var e = Lot690.Attendre(coutume, "lecture des comptes au tick " + N(tick + 1)); e.MoveNext();) yield return null;
            if (!coutume.Result.Presente || coutume.Result.Donnees.Part == null) throw Echec("comptes au tick " + N(tick + 1) + " : " + (coutume.Result.Absence ?? "part absente"));
            string partCoutumiere = (coutume.Result.Donnees.Part.Value * 100).ToString("0.##", Fr);
            if (partCoutumiere != "3") throw Echec("part coutumière servie " + partCoutumiere + " %, attendu 3 %");
            for (var e = Lot690.Jusqua(() => Dit(dossier.TexteAffiche, partie.Monde.Donnees.Monde.Date, partCoutumiere), () => "3 % au tick " + N(tick + 1) + " attendu, feuillet « " + Ligne(dossier.TexteAffiche) + " »"); e.MoveNext();) yield return null;

            var depot = Task.Run(() => { using (var c = new ClientIntention(port, TimeSpan.FromSeconds(ATTENTE_S))) return c.Deposer(OrdresMaison.Part(maison, "25")); });
            for (var e = Lot690.Attendre(depot, "dépôt de la part de 25 %"); e.MoveNext();) yield return null;
            if (!depot.Result.Acceptee) throw Echec("part de 25 % refusée : " + (depot.Result.Presente ? depot.Result.Erreur : depot.Result.Absence));
            if (!Environment.GetCommandLineArgs().Contains(SANS_TICK))
            {
                var trente = Pousser(port, JOURS);
                for (var e = Lot690.Attendre(trente, "POST /tick?n=" + JOURS); e.MoveNext();) yield return null;
                if (trente.Result.statut != 200) throw Echec("POST /tick?n=" + JOURS + " a rendu " + trente.Result.statut + " : " + trente.Result.corps);
            }
            long fin = tick + 1 + JOURS; double echeance = Time.realtimeSinceStartupAsDouble + ATTENTE_RELECTURE_S;
            while (horloge.Lue?.Tick != fin || !Dit(dossier.TexteAffiche, horloge.Lue.Date, "25")) // sans toucher au feuillet : il se relit seul
            {
                if (Time.realtimeSinceStartupAsDouble > echeance) throw Echec("25 % au tick " + N(fin) + " attendu en " + ATTENTE_RELECTURE_S + " s, feuillet « " + Ligne(dossier.TexteAffiche) + " »");
                yield return null;
            }
            var apres = Comptes(port, maison); var monde = Lot690.LireMonde(port);
            for (var e = Lot690.Attendre(Task.WhenAll(apres, monde), "lecture des comptes et du monde au tick " + N(fin)); e.MoveNext();) yield return null;
            Lot690.ExigerMonde(monde.Result, fin, maison, "après trente jours");
            if (!apres.Result.Presente || apres.Result.Donnees.Part != 0.25) throw Echec("comptes au tick " + N(fin) + " : part " + apres.Result.Donnees?.Part + " " + apres.Result.Absence + ", attendu 0,25");
            string preleve = "Prélevé : " + TexteDuMonde.Masse(apres.Result.Donnees.Flux.PreleveKg);
            if (!dossier.TexteAffiche.Contains(preleve + Environment.NewLine)) throw Echec("« " + preleve + " » absent du feuillet « " + Ligne(dossier.TexteAffiche) + " »");

            // La photo : la caméra prend toute l'image, et la toile du cabinet (overlay, invisible de la caméra de capture) se dessine sur elle.
            RectTransform panneau = toile.Cast<Transform>().OfType<RectTransform>().SingleOrDefault(t => t.name == FEUILLET && t.GetComponentInChildren<ScrollRect>(true) != null)
                ?? throw Echec("panneau du feuillet « " + FEUILLET + " » introuvable dans la toile");
            Text texte = panneau.GetComponentsInChildren<Text>(true).SingleOrDefault(t => t.text == dossier.TexteAffiche) ?? throw Echec("le feuillet ne montre pas son texte");
            Lot549.Photographier(camera, carte);
            camera.rect = new Rect(0, 0, 1, 1);
            Canvas cabinetToile = toile.GetComponent<Canvas>();
            cabinetToile.renderMode = RenderMode.ScreenSpaceCamera; cabinetToile.worldCamera = camera; cabinetToile.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases();
            Lisible(camera, panneau, texte);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (horloge.Lue?.Tick != fin || !Dit(dossier.TexteAffiche, horloge.Lue.Date, "25") || texte.text != dossier.TexteAffiche || cabinet.Partie.Monde?.Donnees.MaisonDuJoueur != maison)
                throw Echec("après la pose : feuillet « " + Ligne(dossier.TexteAffiche) + " », maison « " + cabinet.Partie.Monde?.Donnees.MaisonDuJoueur + " »");
            Lisible(camera, panneau, texte);
            Dossier = dossier; Texte = texte; ComptesLus = apres.Result.Donnees; Port = port;
            Debug.Log("CAPTURE_655 maison " + maison + " (" + SIEGE + "), ticks " + N(tick) + " → " + N(tick + 1) + " → " + N(fin) + ", part " + partCoutumiere + " % → 25 %, feuillet « " + Ligne(dossier.TexteAffiche) + " »");
        }

        // Le panneau ouvert, dans le champ, et son texte entier dans la fenêtre défilante : rien n'est coupé.
        static void Lisible(Camera camera, RectTransform panneau, Text texte)
        {
            if (!panneau.gameObject.activeInHierarchy) throw Echec("le feuillet est fermé");
            Lot690.DansLeChamp(camera, texte);
            RectTransform fenetre = panneau.GetComponentInChildren<ScrollRect>(true).viewport;
            if (texte.preferredHeight > fenetre.rect.height) throw Echec("feuillet tronqué : " + texte.preferredHeight + " px de texte pour " + fenetre.rect.height + " px");
        }
        static Task<Lecture<ComptesDeMaison>> Comptes(int port, string maison) =>
            Task.Run(() => { using (var c = new ClientMaison(port, TimeSpan.FromSeconds(ATTENTE_S))) return c.LireComptes(maison); });
        static Task<(int statut, string corps)> Pousser(int port, int jours) => Task.Run(() => {
            using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(ATTENTE_S) }) using (var contenu = new ByteArrayContent(new byte[0]))
            using (var reponse = http.PostAsync("http://127.0.0.1:" + port + "/tick?n=" + jours, contenu).GetAwaiter().GetResult())
                return ((int)reponse.StatusCode, reponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()); });
    }
}
