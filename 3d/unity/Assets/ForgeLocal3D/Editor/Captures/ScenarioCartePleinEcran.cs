using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // La carte qui prend tout l'écran, branchée au service et photographiée cinq fois, chaque image partant de l'état de la précédente :
    //   1-europe         la France choisie et « Commencer » pressé, puis la vue ramenée à toute la carte : la caméra regarde d'en haut, le nord
    //                    en haut, sur tout l'écran ; l'accueil, « Votre maison » et la fiche d'une terre sont fermés, « Ma capitale » est là ;
    //   2-france         « Ma capitale » pressé : la vue se pose sur le siège servi, à la demi-hauteur du siège ; puis la molette recule,
    //                    sous le milieu de l'écran, jusqu'à ce que le nom « France », trop grand de si près, se lise en entier ;
    //   3-province       au plus près : une province, ses lieux lus et aucune figurine de lieu posée ;
    //   4-fiche-ouverte  le temps arrêté, la terre sous le centre de l'écran gardée par le chemin du clic : sa marque, la fiche « Territoire conservé » avec
    //                    sa croix, et son texte lu au service ;
    //   5-fiche-fermee   la croix de la fiche pressée : la fiche est fermée, la terre relâchée, sa marque ôtée.
    // Chaque scénario vérifie ce qu'il photographie et échoue sinon. Le tick est celui que le service sert, jamais un tick écrit en dur.
    // La toile du cabinet se pose devant la caméra de la carte à chaque scénario, au plan proche de la vue du moment : un plan laissé à
    // l'ancienne échelle passerait derrière le sol quand la vue change de distance.
    static class ScenarioCartePleinEcran
    {
        const string GROUPE = "carte-plein-ecran", FRANCE = "France", CROIX = "Fermer", MAISON = "Votre maison", FICHE = "Territoire conservé", LECTURE = "Lecture du territoire";
        const float TOLERANCE_DU_CENTRE_KM = 5f, TOLERANCE_DE_L_ECHELLE_KM = 0.01f, TOLERANCE_DE_L_ANGLE = 0.01f; const int IMAGES_DE_POSE = 4, CRANS_POUR_LIRE_LE_PAYS = 12;
        const double STABLE_S = 2.5; // le texte de la fiche est récrit une image après la lecture
        static readonly Rect TOUT_L_ECRAN = new Rect(0, 0, 1, 1);

        [ScenarioDeCapture(GROUPE, "1-europe")]
        static IEnumerator Europe(Camera camera)
        {
            var e = ScenarioAccueil.OuvrirLaCarte(); while (e.MoveNext()) yield return e.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            string france = guerre.Terres.Pays.Single(p => p.Nom == FRANCE).Id;
            cabinet.Accueil.Designer(guerre.Terres.Terres.First(t => t.Pays == france).CellId);
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.TexteDuNom == FRANCE && cabinet.Accueil.Montree != null && cabinet.Accueil.Commencer.interactable,
                () => "fiche de la France : « " + cabinet.Accueil.TexteDuNom + " » « " + cabinet.Accueil.TexteDeLaFiche + " »"); a.MoveNext();) yield return null;
            string maison = cabinet.Accueil.Montree.Id;
            var commencer = ScenarioAccueil.CommencerPuisLancer(cabinet); while (commencer.MoveNext()) yield return commencer.Current;
            Button capitale = Capitale(cabinet);
            for (var a = AttentesDeCapture.Jusqua(() => ScenarioAccueil.Servie(cabinet) == maison && cabinet.Partie.Jouable != null && cabinet.Partie.Maison?.Presente == true && capitale.gameObject.activeInHierarchy,
                () => "après « Commencer » : maison « " + ScenarioAccueil.Servie(cabinet) + " », reçu « " + (cabinet.Partie.Recu?.Erreur ?? cabinet.Partie.Recu?.Absence) + " », « Ma capitale » " + capitale.gameObject.activeInHierarchy); a.MoveNext();) yield return null;
            // Toute la carte, comme au premier jour : la maison servie a posé la vue sur son siège, le joueur la recule.
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(carte.Vue.Centre, carte.Vue.DemiMax); carte.Vue.Poser(carte.camera, carte.transform);
            PoserLaToile(carte, cabinet); guerre.SuivreLaVue();
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (carte.camera.rect != TOUT_L_ECRAN) throw Faux("la caméra de la carte ne prend pas tout l'écran : " + carte.camera.rect);
            if (!Mathf.Approximately(carte.Vue.Echelle, 1f)) throw Faux("la vue n'est pas sur toute la carte : échelle " + carte.Vue.Echelle.ToString("0.###", CultureInfo.InvariantCulture));
            VerifierLeRegardVerticalEtNordEnHaut(carte);
            if (cabinet.Accueil.Ouvert || cabinet.Accueil.Panneau.gameObject.activeSelf) throw Faux("l'accueil reste ouvert");
            if (Panneau(cabinet, MAISON).gameObject.activeSelf) throw Faux("« " + MAISON + " » est ouvert sans un clic");
            if (Panneau(cabinet, FICHE).gameObject.activeSelf) throw Faux("« " + FICHE + " » est ouvert sans terre gardée");
            if (!capitale.gameObject.activeInHierarchy) throw Faux("« " + CabinetDeCarte.CAPITALE + " » est absent avec une maison servie au siège placé");
            Debug.Log("CAPTURE carte plein écran : toute la carte au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", demi " + carte.Vue.Demi.ToString("0", CultureInfo.InvariantCulture) + " km, maison « " + maison + " »");
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "2-france")]
        static IEnumerator France(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Button capitale = Capitale(cabinet);
            if (!capitale.gameObject.activeInHierarchy) throw Faux("« " + CabinetDeCarte.CAPITALE + " » n'est pas actif");
            capitale.onClick.Invoke();
            PoserLaToile(carte, cabinet); guerre.SuivreLaVue();
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Vector3 siege = carte.PositionSurLaCarte(cabinet.Partie.Maison.Donnees.Siege.Position.Value, 0f).Value;
            var ici = new Vector2(siege.x, siege.z);
            if ((carte.Vue.Centre - ici).magnitude > TOLERANCE_DU_CENTRE_KM) throw Faux("la vue n'est pas sur le siège : centre " + carte.Vue.Centre + " pour " + ici);
            if (Mathf.Abs(carte.Vue.Demi - CabinetDeCarte.DEMI_SUR_LE_SIEGE_KM) > TOLERANCE_DE_L_ECHELLE_KM) throw Faux("la demi-hauteur n'est pas celle du siège : " + carte.Vue.Demi + " km pour " + CabinetDeCarte.DEMI_SUR_LE_SIEGE_KM);
            NomCourbe nom = guerre.NomsDesPays.SingleOrDefault(n => n.Texte == FRANCE) ?? throw Faux("« " + FRANCE + " » n'est pas écrit sur la carte");
            string Hors() => string.Join(", ", nom.Compose.Lettres.Select((l, k) => (v: carte.camera.WorldToViewportPoint(carte.transform.TransformPoint(new Vector3(l.Point.x, 0f, l.Point.y))), k))
                .Where(l => l.v.z <= 0f || l.v.x < 0f || l.v.x > 1f || l.v.y < 0f || l.v.y > 1f).Select(l => "lettre " + l.k + " " + l.v));
            // Sur le siège, le nom du pays est trop grand et s'efface : le joueur recule d'un cran de molette à la fois, sous le
            // milieu de l'écran, jusqu'à le lire en entier.
            int crans = 0;
            for (; crans < CRANS_POUR_LIRE_LE_PAYS && (nom.Opacite <= 0f || Hors().Length > 0); crans++)
            {
                carte.Vue.Zoomer(-1f, new Vector2(.5f, .5f)); carte.Vue.Poser(carte.camera, carte.transform); PoserLaToile(carte, cabinet); guerre.SuivreLaVue();
                for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            }
            string hors = Hors(); if (hors.Length > 0) throw Faux("« " + FRANCE + " » sort de l'image après " + crans + " crans : " + hors);
            if (nom.Opacite <= 0f) throw Faux("« " + FRANCE + " » reste caché après " + crans + " crans de recul (" + nom.CorpsPx.ToString("0.#", CultureInfo.InvariantCulture) + " px)");
            if ((carte.Vue.Centre - ici).magnitude > TOLERANCE_DU_CENTRE_KM) throw Faux("en reculant sous le milieu de l'écran, la vue a quitté le siège : " + carte.Vue.Centre);
            Debug.Log("CAPTURE carte plein écran : le siège au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", centre " + carte.Vue.Centre + ", demi " + carte.Vue.Demi.ToString("0", CultureInfo.InvariantCulture)
                + " km après " + crans + " crans de recul ; « " + FRANCE + " » à " + nom.CorpsPx.ToString("0", CultureInfo.InvariantCulture) + " px, opacité " + nom.Opacite.ToString("0.##", CultureInfo.InvariantCulture));
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "3-province")]
        static IEnumerator Province(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var lieux = carte.GetComponent<LieuxDeCarte>() ?? throw Faux("pas de lieux sur la carte");
            carte.Vue.Zoomer(1000f, new Vector2(.5f, .5f)); carte.Vue.Poser(carte.camera, carte.transform);
            PoserLaToile(carte, cabinet); guerre.SuivreLaVue();
            for (var a = AttentesDeCapture.Jusqua(() => lieux.Peint && lieux.TexteLegende.Length > LieuxDeCarte.ENTETE.Length,
                () => "lieux peints " + lieux.Peint + ", lecture en vol " + lieux.LectureEnVol); a.MoveNext();) yield return null;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (Mathf.Abs(carte.Vue.Demi - VueDeCarte.DEMI_MIN_KM) >= 1e-3f) throw Faux("la vue n'est pas au plus près : demi " + carte.Vue.Demi + " km pour " + VueDeCarte.DEMI_MIN_KM);
            // Les lieux se lisent mais ne posent aucune figurine : leur forme est sur le terrain.
            var posees = carte.GetComponentsInChildren<Transform>(true).Where(t => t.name == "Lieux de la carte" || t.name.StartsWith("Lieu ", StringComparison.Ordinal)).Select(t => t.name).ToArray();
            if (posees.Length > 0) throw Faux("des figurines de lieux sont posées sur la carte : " + string.Join(", ", posees));
            Debug.Log("CAPTURE carte plein écran : la province au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", demi " + carte.Vue.Demi.ToString("0.###", CultureInfo.InvariantCulture) + " km, " + lieux.EnAlerte.Count + " lieux en alerte, aucune figurine de lieu");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "4-fiche-ouverte")]
        static IEnumerator FicheOuverte(Camera camera)
        {
            var (carte, cabinet, _) = ScenarioAccueil.Lire();
            PoserLaToile(carte, cabinet);
            // Le temps arrêté, comme le joueur qui lit une fiche : elle suit chaque jour du monde, et ne se fixerait pas sinon.
            var horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Faux("pas d'horloge sur la carte");
            if (horloge.Lue == null || horloge.Lue.JoursParSeconde != 0) horloge.Basculer();
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue != null && horloge.Lue.JoursParSeconde == 0, () => "le temps ne s'arrête pas : " + horloge.Lue?.JoursParSeconde + " jours par seconde"); a.MoveNext();) yield return null;
            Vector2 ici = carte.camera.ViewportToScreenPoint(new Vector3(.5f, .5f, 0f));
            var fiche = carte.GetComponent<FicheDeCellule>() ?? throw Faux("pas de fiche de cellule sur la carte");
            fiche.Survoler(ici);
            if (fiche.Survolee == null) throw Faux("aucune terre sous le centre de l'écran " + ici);
            cabinet.Noter(ici, true, false, false, fiche.Survolee);
            if (!cabinet.Noter(ici, false, true, false, fiche.Survolee)) throw Faux("le clic sur la terre sous le centre de l'écran ne la garde pas");
            if (cabinet.Retenue == null) throw Faux("aucune terre gardée après le clic");
            RectTransform panneau = Panneau(cabinet, FICHE);
            for (var a = AttentesDeCapture.Jusqua(() => panneau.gameObject.activeSelf, () => "« " + FICHE + " » ne s'ouvre pas avec la terre " + cabinet.Retenue.CellId); a.MoveNext();) yield return null;
            Transform croix = panneau.Find(CROIX);
            if (croix == null || !croix.gameObject.activeInHierarchy || croix.GetComponent<Button>() == null) throw Faux("la croix de « " + FICHE + " » est absente, cachée ou sans bouton");
            if (carte.Marquee != cabinet.Retenue.CellId) throw Faux("la terre gardée n'est pas marquée sur la carte : marque " + carte.Marquee + " pour " + cabinet.Retenue.CellId);
            // Le texte est lu au service : il quitte l'attente et l'échec, puis ne bouge plus.
            var dossier = carte.GetComponent<DossierTerritoire>() ?? throw Faux("pas de dossier du territoire");
            Text texte = panneau.Find(LECTURE)?.GetComponentInChildren<Text>(true) ?? throw Faux("« " + LECTURE + " » est absent de la fiche");
            bool Lu() => dossier.Document != null && !texte.text.Contains(DossierTerritoire.ATTENTE) && !texte.text.Contains(DossierTerritoire.PAYS_EN_LECTURE)
                && !texte.text.Contains("Lecture indisponible");
            for (var a = AttentesDeCapture.Jusqua(Lu, () => "texte de la fiche : « " + texte.text + " », document lu " + (dossier.Document != null)); a.MoveNext();) yield return null;
            string avant = texte.text; double depuis = Time.realtimeSinceStartupAsDouble, fin = depuis + 20;
            while (Time.realtimeSinceStartupAsDouble - depuis < STABLE_S && Time.realtimeSinceStartupAsDouble < fin)
            {
                yield return null;
                if (texte.text != avant) { avant = texte.text; depuis = Time.realtimeSinceStartupAsDouble; }
            }
            if (!Lu() || Time.realtimeSinceStartupAsDouble - depuis < STABLE_S) throw Faux("le texte de la fiche ne se fixe pas : « " + texte.text + " »");
            Debug.Log("CAPTURE carte plein écran : la terre " + cabinet.Retenue.CellId + " gardée au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + " ; fiche de " + texte.text.Length + " signes : « " + texte.text.Split('\n')[0] + " »");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "5-fiche-fermee")]
        static IEnumerator FicheFermee(Camera camera)
        {
            var (carte, cabinet, _) = ScenarioAccueil.Lire();
            RectTransform panneau = Panneau(cabinet, FICHE);
            Button croix = panneau.Find(CROIX)?.GetComponent<Button>() ?? throw Faux("la croix de « " + FICHE + " » est absente");
            if (cabinet.Retenue == null || !panneau.gameObject.activeSelf) throw Faux("la fiche n'est pas ouverte : « 4-fiche-ouverte » n'a pas réussi");
            croix.onClick.Invoke();
            PoserLaToile(carte, cabinet);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (panneau.gameObject.activeSelf) throw Faux("« " + FICHE + " » reste ouvert après la croix");
            if (cabinet.Retenue != null) throw Faux("la terre " + cabinet.Retenue.CellId + " reste gardée après la croix");
            if (carte.Marquee != null) throw Faux("la terre " + carte.Marquee + " reste marquée après la croix");
            Debug.Log("CAPTURE carte plein écran : la fiche fermée au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick);
            yield return carte.camera;
        }

        // La toile du cabinet au plan proche courant de la caméra de la carte, qui suit la distance de la vue.
        static void PoserLaToile(CarteDessinee carte, CabinetDeCarte cabinet) =>
            cabinet.transform.Find("Cabinet").GetComponent<Canvas>().planeDistance = carte.camera.nearClipPlane + ScenarioAccueil.ECART_DE_PLAN;

        static RectTransform Panneau(CabinetDeCarte cabinet, string nom) => (RectTransform)cabinet.transform.Find("Cabinet/" + nom) ?? throw Faux("« " + nom + " » absent du cabinet");

        static Button Capitale(CabinetDeCarte cabinet) =>
            cabinet.transform.Find("Cabinet").GetComponentsInChildren<Button>(true).SingleOrDefault(b => b.name == CabinetDeCarte.CAPITALE) ?? throw Faux("« " + CabinetDeCarte.CAPITALE + " » absent du cabinet");

        // La caméra regarde le sol d'aplomb, le nord en haut de l'image, dans le repère de la carte.
        static void VerifierLeRegardVerticalEtNordEnHaut(CarteDessinee carte)
        {
            float regard = Vector3.Angle(carte.camera.transform.forward, carte.transform.TransformDirection(Vector3.down)), haut = Vector3.Angle(carte.camera.transform.up, carte.transform.TransformDirection(Vector3.forward));
            if (regard > TOLERANCE_DE_L_ANGLE) throw Faux("la caméra ne regarde pas à la verticale : " + regard.ToString("0.###", CultureInfo.InvariantCulture) + "° d'écart");
            if (haut > TOLERANCE_DE_L_ANGLE) throw Faux("le nord n'est pas en haut de l'image : " + haut.ToString("0.###", CultureInfo.InvariantCulture) + "° d'écart");
        }

        static InvalidOperationException Faux(string raison) => new InvalidOperationException("carte plein écran : " + raison);
    }
}
