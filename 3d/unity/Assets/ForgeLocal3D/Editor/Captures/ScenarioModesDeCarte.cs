using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Les cinq modes de la carte, choisis chacun d'un clic de pointeur sur son bouton à l'écran, contre le vrai service, en 1920 × 1080 :
    //   1-politique     la France choisie et « Commencer » pressé, le temps arrêté, la vue sur toute l'Europe : les pays, leurs noms ;
    //   2-relief        le terrain nu : chaque terre à la teinte de sa classe de relief servie, aucune au pigment d'un pays, aucun nom de pays ;
    //   3-population    du clair au foncé : la terre la plus peuplée est plus foncée que la moins peuplée ;
    //   4-vivres        puis « Ma capitale » pressé : la vue sur Paris, où les flèches des lieux vers le siège se voient ;
    //   5-guerres       la France déclare la guerre à l'Angleterre (l'intention du joueur), la vue revient sur l'Europe : seuls les
    //                   pays que `/guerres` dit en guerre gardent leur couleur ;
    //   6-ma-capitale   la carte politique de nouveau, puis « Ma capitale » : la vue sur le siège.
    // Chaque image vérifie ce qu'elle montre et échoue sinon : le bouton du mode enfoncé, et lui seul ; la légende du mode, datée du jour
    // que le service sert ; la caméra qui ne bouge pas quand le mode change. Le tick est celui que le service sert, jamais écrit en dur.
    static class ScenarioModesDeCarte
    {
        const string GROUPE = "modes-de-carte", FRANCE = "France", ANGLETERRE = "Angleterre";
        const int LARGEUR = 1920, HAUTEUR = 1080, IMAGES_DE_POSE = 6;
        const double STABLE_S = 2.5; // les textes du cabinet sont récrits une image après la lecture
        const float TOLERANCE_DU_CENTRE_KM = 5f;

        [ScenarioDeCapture(GROUPE, "1-politique", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator Politique(Camera camera)
        {
            var e = ScenarioAccueil.OuvrirLaCarte(); while (e.MoveNext()) yield return e.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            // Sans écran, la vue du jeu est petite : les étiquettes et la toile s'y régleraient pour elle. La caméra de la carte rend
            // dans un écran de la taille de la photo, et tout s'y règle, les clics compris.
            if (carte.camera.targetTexture == null) carte.camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24) { name = "Écran des modes de carte" };
            carte.camera.aspect = (float)LARGEUR / HAUTEUR;
            string france = guerre.Terres.Pays.Single(p => p.Nom == FRANCE).Id;
            cabinet.Accueil.Designer(guerre.Terres.Terres.First(t => t.Pays == france).CellId);
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.TexteDuNom == FRANCE && cabinet.Accueil.Montree != null && cabinet.Accueil.Commencer.interactable,
                () => "fiche de la France : « " + cabinet.Accueil.TexteDuNom + " »"); a.MoveNext();) yield return null;
            string maison = cabinet.Accueil.Montree.Id;
            Cliquer(carte, cabinet.Accueil.Commencer);
            for (var a = AttentesDeCapture.Jusqua(() => ScenarioAccueil.Servie(cabinet) == maison && cabinet.Partie.Maison?.Presente == true && Capitale(cabinet).gameObject.activeInHierarchy,
                () => "après « Commencer » : maison « " + ScenarioAccueil.Servie(cabinet) + " »"); a.MoveNext();) yield return null;
            // Le temps arrêté : la date servie ne bouge plus pendant les photos.
            var horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Faux("pas d'horloge sur la carte");
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue != null, () => "horloge non lue"); a.MoveNext();) yield return null;
            if (horloge.Lue.JoursParSeconde != 0) horloge.Basculer();
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue != null && horloge.Lue.JoursParSeconde == 0, () => "le temps ne s'arrête pas"); a.MoveNext();) yield return null;
            var t = ToutLEurope(carte, cabinet, guerre); while (t.MoveNext()) yield return null;
            var calques = Calques(carte);
            if (calques.Mode != ModeDeCarte.Politique) throw Faux("la carte ne s'ouvre pas sur le mode Politique : " + calques.Mode);
            // La planche d'icônes livrée se montre sur chaque bouton, à la place du signe gravé.
            foreach (ModeDeCarte mode in Enum.GetValues(typeof(ModeDeCarte)))
            {
                string motif = EmblemeCommande.Motif(mode.ToString()); Transform bouton = calques.BoutonDu(mode).transform, icone = bouton.Find(CalquesCarte.ICONE + motif);
                bool livree = Resources.Load<Texture2D>(CalquesCarte.Planche(mode)) != null;
                if (livree && (icone == null || !icone.gameObject.activeInHierarchy || bouton.Find("Repère " + motif).gameObject.activeSelf)) throw Faux("« " + mode + " » ne montre pas l'icône livrée de la planche");
                Debug.Log("CAPTURE modes de carte : « " + mode + " » montre " + (livree ? "l'icône de la planche" : "le signe gravé (planche non livrée)"));
            }
            var c = Choisir(ModeDeCarte.Politique, () => "Pays au " + TexteDuMonde.Date(guerre.Terres.Date)); while (c.MoveNext()) yield return null;
            if (!carte.PaysMontres || !guerre.NomsMontres || guerre.NomsDesPays.Count(n => n.Opacite > 0f) == 0) throw Faux("la carte politique ne montre ni frontières ni noms de pays");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "2-relief", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator Relief(Camera camera)
        {
            var (carte, _, guerre) = ScenarioAccueil.Lire();
            var c = Choisir(ModeDeCarte.Relief, () => "Relief servi, qui ne change pas"); while (c.MoveNext()) yield return null;
            var relief = new ReliefDesTerres(carte.Lue); var pigments = new HashSet<Color32>(guerre.Terres.Pays.Select(p => (Color32)guerre.CouleurDuPays(p.Id)));
            int peintes = 0;
            foreach (var cellule in carte.Lue.Cellules)
            {
                if (!(carte.TeinteDe(cellule.CellId) is Color teinte)) continue; peintes++;
                if (pigments.Contains(teinte)) throw Faux("la terre " + cellule.CellId + " garde le pigment d'un pays en mode Relief");
                if (!((Color32)teinte).Equals((Color32)relief.Teinte(cellule.CellId))) throw Faux("la terre " + cellule.CellId + " n'a pas la teinte de son relief servi « " + cellule.Relief + " »");
            }
            if (peintes == 0) throw Faux("aucune terre peinte");
            if (carte.PaysMontres || guerre.NomsMontres || guerre.Ecriture.Racine.gameObject.activeInHierarchy) throw Faux("les frontières ou les noms des pays se voient en mode Relief");
            Debug.Log("CAPTURE modes de carte : relief sur " + peintes + " terres, " + relief.SansRelief + " sans relief servi");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "3-population", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator Population(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var c = Choisir(ModeDeCarte.Population, () => TexteDuMonde.Date(Monde(cabinet).Date)); while (c.MoveNext()) yield return null;
            // La densité de chaque terre : ses habitants servis par `/monde`, divisés par son aire servie par `/carte`.
            var aires = carte.Lue.Cellules.ToDictionary(x => x.CellId, x => x.AireKm2);
            if (aires.Values.Any(a => !(a > 0))) throw Faux("une terre n'a pas d'aire servie par /carte");
            var peintes = Monde(cabinet).Cellules.Where(x => carte.TeinteDe(x.CellId).HasValue && x.CellId != cabinet.Retenue?.CellId).Select(x => (x.CellId, densite: x.Population / aires[x.CellId])).ToList();
            var plus = peintes.OrderByDescending(x => x.densite).First(); var moins = peintes.OrderBy(x => x.densite).First();
            float Clair(long cell) => carte.TeinteDe(cell).Value.grayscale;
            if (plus.densite <= moins.densite) throw Faux("échantillon vide : toutes les terres ont la même densité");
            if (!(Clair(plus.CellId) < Clair(moins.CellId))) throw Faux("la terre la plus dense (" + RepartitionHabitants.Densite(plus.densite) + ") n'est pas plus foncée que la moins dense (" + RepartitionHabitants.Densite(moins.densite) + ")");
            if (!Calques(carte).Legende.text.Contains("hab./km²")) throw Faux("la légende de la population ne dit pas sa densité en hab./km²");
            // La densité de quelques pays, toutes leurs terres ensemble : à poser à côté de l'atlas.
            var monde = Monde(cabinet).Cellules.ToDictionary(x => x.CellId, x => x.Population);
            string DuPays(string nom) { var terres = guerre.Terres.Terres.Where(t => t.Pays != null && guerre.Terres.NomDuPays(t.Pays) == nom && monde.ContainsKey(t.CellId)).ToList();
                return terres.Count == 0 ? nom + " sans terre" : nom + " " + RepartitionHabitants.Densite(terres.Sum(t => monde[t.CellId]) / terres.Sum(t => aires[t.CellId])); }
            Debug.Log("CAPTURE modes de carte : densité de " + RepartitionHabitants.Densite(moins.densite) + " à " + RepartitionHabitants.Densite(plus.densite) + " ; "
                + string.Join(", ", new[] { "France", "Lituanie", "Angleterre", "Castille", "Milan", "Mamelouks" }.Select(DuPays)));
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "4-vivres", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator Vivres(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var c = Choisir(ModeDeCarte.Vivres, () => "Vivres au " + TexteDuMonde.Date(Monde(cabinet).Date)); while (c.MoveNext()) yield return null;
            // La vue sur la capitale, d'un clic sur « Ma capitale », où les flèches des lieux vers le siège se lisent.
            Cliquer(carte, Capitale(cabinet)); PoserLaToile(carte, cabinet); guerre.SuivreLaVue();
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            VerifierLeSiege(carte, cabinet);
            var fleches = carte.GetComponent<FlechesDeCarte>() ?? throw Faux("pas de flèches sur la carte");
            Transform racine = null;
            bool Montrees() => (racine = carte.transform.Find(FlechesDeCarte.RACINE)) != null && racine.gameObject.activeInHierarchy && racine.Cast<Transform>().Any(f => Dans(carte, f.GetComponent<MeshRenderer>().bounds.center));
            string Bulle() => Calques(carte).Legende.GetComponentInParent<Infobulle>().Phrase;
            for (var a = AttentesDeCapture.Jusqua(() => Montrees() || Bulle().Contains("Aucune flèche"), () => "aucune flèche montrée, et la légende ne le dit pas : " + fleches.TexteLegende); a.MoveNext();) yield return null;
            var s = Stable(carte); while (s.MoveNext()) yield return null;
            int montrees = racine == null ? 0 : racine.Cast<Transform>().Count(f => Dans(carte, f.GetComponent<MeshRenderer>().bounds.center));
            Debug.Log("CAPTURE modes de carte : vivres sur la capitale, " + montrees + " flèches dans l'image ; « " + Calques(carte).Legende.text.Replace("\n", " | ") + " »");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "5-guerres", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator Guerres(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            // Le joueur déclare la guerre à l'Angleterre par l'intention que le service attend, puis un jour passe.
            string maison = ScenarioAccueil.Servie(cabinet), anglais = guerre.Terres.Terres.First(t => t.Pays == Pays(guerre, ANGLETERRE)).Maitre;
            GestesDeCapture.Deposer(carte.port, IntentionsDeGuerre.Declarer(maison, anglais)); GestesDeCapture.Tick(carte.port);
            for (var a = AttentesDeCapture.Jusqua(() => guerre.Guerres != null && guerre.Guerres.Guerres.Count > 0, () => "aucune guerre servie après la déclaration : " + (guerre.AbsenceDesGuerres ?? "guerres lues vides")); a.MoveNext();) yield return null;
            var t = ToutLEurope(carte, cabinet, guerre); while (t.MoveNext()) yield return null;
            var c = Choisir(ModeDeCarte.Guerres, () => "Guerres au " + TexteDuMonde.Date(guerre.Guerres.Date)); while (c.MoveNext()) yield return null;
            // Les pays en guerre, lus de `/guerres` : chaque maison ramenée au pays des terres dont elle tient le bourg.
            var enGuerre = new HashSet<string>(guerre.Guerres.Guerres.SelectMany(g => new[] { guerre.PaysDeLaMaison(g.Agresseur), guerre.PaysDeLaMaison(g.Defenseur) }));
            var assiegees = new HashSet<long>(guerre.Guerres.Armees.Where(x => x.Siege != null).Select(x => x.Siege.Value));
            int marquees = 0;
            foreach (var terre in guerre.Terres.Terres)
            {
                if (!(carte.TeinteDe(terre.CellId) is Color teinte) || terre.CellId == cabinet.Retenue?.CellId || assiegees.Contains(terre.CellId)) continue;
                bool marquee = terre.Pays != null && ((Color32)teinte).Equals((Color32)guerre.CouleurDuPays(terre.Pays)) && !((Color32)teinte).Equals((Color32)BelligerantsDesPays.EN_PAIX);
                if (marquee && !enGuerre.Contains(terre.Pays)) throw Faux("la terre " + terre.CellId + " de " + guerre.Terres.NomDuPays(terre.Pays) + ", en paix, est marquée");
                if (!marquee && enGuerre.Contains(terre.Pays)) throw Faux("la terre " + terre.CellId + " de " + guerre.Terres.NomDuPays(terre.Pays) + ", en guerre, n'est pas marquée");
                if (marquee) marquees++;
            }
            if (marquees == 0) throw Faux("aucune terre d'un pays en guerre n'est marquée");
            int dessinees = guerre.NombresDesArmees.Count, servies = guerre.Guerres.Armees.Count(x => carte.PositionSurLaCarte(x.Point, 0f) != null);
            if (dessinees != servies) throw Faux(servies + " armées servies sur la carte, " + dessinees + " dessinées");
            Debug.Log("CAPTURE modes de carte : " + guerre.Guerres.Guerres.Count + " guerres servies, pays en guerre " + string.Join(", ", enGuerre.Select(p => guerre.Terres.NomDuPays(p) ?? p))
                + ", " + marquees + " terres marquées, " + dessinees + " armées dessinées, " + assiegees.Count + " terres assiégées");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "6-ma-capitale", Largeur = LARGEUR, Hauteur = HAUTEUR)]
        static IEnumerator MaCapitale(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var c = Choisir(ModeDeCarte.Politique, () => "Pays au " + TexteDuMonde.Date(guerre.Terres.Date)); while (c.MoveNext()) yield return null;
            Cliquer(carte, Capitale(cabinet)); PoserLaToile(carte, cabinet); guerre.SuivreLaVue();
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            VerifierLeSiege(carte, cabinet);
            if (!Calques(carte).Enfonce(ModeDeCarte.Politique)) throw Faux("« Ma capitale » a changé le mode enfoncé");
            var s = Stable(carte); while (s.MoveNext()) yield return null;
            yield return carte.camera;
        }

        // Le mode choisi d'un clic sur son bouton : il s'enfonce, et lui seul ; la caméra ne bouge pas ; la légende dit le mode et le
        // texte attendu (sa date, lue au service), jamais une indisponibilité, et elle ne bouge plus.
        static IEnumerator Choisir(ModeDeCarte mode, Func<string> attendu)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire(); var calques = Calques(carte);
            Vector3 place = carte.camera.transform.position; Quaternion regard = carte.camera.transform.rotation; Vector2 centre = carte.Vue.Centre; float demi = carte.Vue.Demi;
            Cliquer(carte, calques.BoutonDu(mode));
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (calques.Mode != mode) throw Faux("le clic sur « " + mode + " » ne change pas le mode : " + calques.Mode);
            string enfonces = string.Join(", ", ((ModeDeCarte[])Enum.GetValues(typeof(ModeDeCarte))).Where(calques.Enfonce));
            if (enfonces != mode.ToString()) throw Faux("boutons enfoncés : « " + enfonces + " » pour le mode " + mode);
            if (carte.camera.transform.position != place || carte.camera.transform.rotation != regard || carte.Vue.Centre != centre || carte.Vue.Demi != demi)
                throw Faux("choisir « " + mode + " » a bougé la caméra : centre " + centre + " → " + carte.Vue.Centre + ", demi " + demi + " → " + carte.Vue.Demi);
            string Texte() => calques.Legende.text;
            for (var a = AttentesDeCapture.Jusqua(() => Texte().Contains(attendu()), () => "légende du mode " + mode + " : « " + Texte() + " », attendu « " + attendu() + " »"); a.MoveNext();) yield return null;
            if (Texte().StartsWith("Mode ", StringComparison.Ordinal) || Texte().StartsWith("Pays indisponibles", StringComparison.Ordinal) || Texte() == CalquesCarte.COUPEE) throw Faux("mode " + mode + " indisponible : « " + Texte() + " »");
            var s = Stable(carte); while (s.MoveNext()) yield return null;
            Debug.Log("CAPTURE modes de carte : " + mode + " au tick " + Monde(cabinet).Tick + " ; « " + Texte().Replace("\n", " | ") + " »");
        }

        // Un clic de pointeur au centre du bouton, tel que l'écran le montre : ce qui est sous le pointeur reçoit le clic, et ce doit être le bouton.
        static void Cliquer(CarteDessinee carte, Button bouton)
        {
            var systeme = EventSystem.current ?? Object.FindFirstObjectByType<EventSystem>() ?? throw Faux("aucun système d'événements dans la scène");
            Canvas.ForceUpdateCanvases();
            var coins = new Vector3[4]; ((RectTransform)bouton.transform).GetWorldCorners(coins);
            Vector2 ici = RectTransformUtility.WorldToScreenPoint(carte.camera, (coins[0] + coins[2]) / 2f);
            var pointeur = new PointerEventData(systeme) { position = ici, button = PointerEventData.InputButton.Left };
            var touches = new List<RaycastResult>(); systeme.RaycastAll(pointeur, touches);
            if (touches.Count == 0) throw Faux("rien sous le pointeur en " + ici + " pour « " + bouton.name + " »");
            GameObject sous = ExecuteEvents.GetEventHandler<IPointerClickHandler>(touches[0].gameObject);
            if (sous != bouton.gameObject) throw Faux("sous le pointeur en " + ici + " : « " + (sous != null ? sous.name : touches[0].gameObject.name) + " », et non « " + bouton.name + " »");
            if (!bouton.interactable) throw Faux("« " + bouton.name + " » est inactif");
            pointeur.pointerCurrentRaycast = pointeur.pointerPressRaycast = touches[0]; pointeur.pointerPress = sous; pointeur.rawPointerPress = touches[0].gameObject;
            ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerEnterHandler); ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerDownHandler);
            ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerUpHandler); ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerClickHandler);
            ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerExitHandler);
        }

        // Toute la carte, comme au premier jour : la vue reculée jusqu'à l'Europe entière.
        static IEnumerator ToutLEurope(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre)
        {
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(carte.Vue.Centre, carte.Vue.DemiMax); carte.Vue.Poser(carte.camera, carte.transform);
            PoserLaToile(carte, cabinet); guerre.SuivreLaVue();
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (!Mathf.Approximately(carte.Vue.Echelle, 1f)) throw Faux("la vue n'est pas sur toute la carte : échelle " + carte.Vue.Echelle.ToString("0.###", CultureInfo.InvariantCulture));
        }

        // La légende et son infobulle ne bougent plus pendant STABLE_S.
        static IEnumerator Stable(CarteDessinee carte)
        {
            var calques = Calques(carte); string Etat() => calques.Legende.text + "|" + calques.Legende.GetComponentInParent<Infobulle>().Phrase;
            string avant = Etat(); double depuis = Time.realtimeSinceStartupAsDouble, fin = depuis + 20;
            while (Time.realtimeSinceStartupAsDouble - depuis < STABLE_S && Time.realtimeSinceStartupAsDouble < fin)
            {
                yield return null; string maintenant = Etat();
                if (maintenant != avant) { avant = maintenant; depuis = Time.realtimeSinceStartupAsDouble; }
            }
        }

        static void VerifierLeSiege(CarteDessinee carte, CabinetDeCarte cabinet)
        {
            Vector3 siege = carte.PositionSurLaCarte(cabinet.Partie.Maison.Donnees.Siege.Position.Value, 0f).Value;
            if ((carte.Vue.Centre - new Vector2(siege.x, siege.z)).magnitude > TOLERANCE_DU_CENTRE_KM) throw Faux("« Ma capitale » ne pose pas la vue sur le siège : centre " + carte.Vue.Centre + " pour " + new Vector2(siege.x, siege.z));
        }

        static bool Dans(CarteDessinee carte, Vector3 monde) { Vector3 v = carte.camera.WorldToViewportPoint(monde); return v.z > 0f && v.x >= 0f && v.x <= 1f && v.y >= 0f && v.y <= 1f; }
        static MondeLu Monde(CabinetDeCarte cabinet) => cabinet.Partie?.Monde?.Presente == true ? cabinet.Partie.Monde.Donnees.Monde : throw Faux("monde non lu");
        static CalquesCarte Calques(CarteDessinee carte) => carte.GetComponent<CalquesCarte>() ?? throw Faux("pas de calques sur la carte");
        static string Pays(CarteDeLaGuerre guerre, string nom) => guerre.Terres.Pays.SingleOrDefault(p => p.Nom == nom)?.Id ?? throw Faux("aucun pays servi ne s'appelle « " + nom + " »");
        static Button Capitale(CabinetDeCarte cabinet) =>
            cabinet.transform.Find("Cabinet").GetComponentsInChildren<Button>(true).SingleOrDefault(b => b.name == CabinetDeCarte.CAPITALE) ?? throw Faux("« " + CabinetDeCarte.CAPITALE + " » absent du cabinet");
        static void PoserLaToile(CarteDessinee carte, CabinetDeCarte cabinet) =>
            cabinet.transform.Find("Cabinet").GetComponent<Canvas>().planeDistance = carte.camera.nearClipPlane + ScenarioAccueil.ECART_DE_PLAN;
        static InvalidOperationException Faux(string raison) => new InvalidOperationException("modes de carte : " + raison);
    }
}
