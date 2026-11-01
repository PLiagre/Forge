using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 883 : le bandeau du cabinet dit la date du monde, « Jour N de 1400 », puis la vitesse ou la pause, sans tick. La capture
    // rejoue les deux scénarios du lot 525 (le monde accélère jusqu'à un jour par seconde, puis se met en pause), pose le cabinet
    // sur la caméra comme `Lot730.Cabinet`, et juge le texte du bandeau. Avec `-forge883Tick`, l'ancien texte, tick compris, est
    // écrit dans le bandeau juste avant le jugement : la contre-épreuve doit échouer sur « tick ».
    static class Lot883
    {
        const string DRAPEAU_TICK = "-forge883Tick";
        const int IMAGES_DE_POSE = 10;

        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);

        [ScenarioDeCapture(883, "01-en-marche")]
        static IEnumerator EnMarche(Camera camera)
        {
            for (var e = Lot525.EnMarche(camera); e.MoveNext();) yield return null;
            HorlogeDeCarte h = Lot525.Horloge ?? throw Echec("l'horloge du lot 525 n'est pas en marche");
            CarteDessinee carte = h.GetComponent<CarteDessinee>() ?? throw Echec("l'horloge n'est pas sur une carte");
            Canvas toile = carte.transform.Find("Cabinet")?.GetComponent<Canvas>() ?? throw Echec("la carte n'a pas de cabinet");
            // Le cabinet se dessine en overlay, invisible d'une seule caméra : la caméra prend toute l'image, décalée vers l'est
            // pour garder la carte à sa place, et la toile du cabinet se dessine sur elle.
            float largeur = camera.rect.width; camera.rect = new Rect(0, 0, 1, 1);
            camera.transform.position += camera.transform.right * (1 - largeur) * camera.orthographicSize * camera.aspect;
            toile.renderMode = RenderMode.ScreenSpaceCamera; toile.worldCamera = camera; toile.planeDistance = camera.nearClipPlane + 0.2f;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            string[] lignes = Juger(camera, h, "en marche");
            if (!lignes[1].EndsWith("par seconde", StringComparison.Ordinal)) throw Echec("en marche : la vitesse dit « " + lignes[1] + " »");
        }

        [ScenarioDeCapture(883, "02-en-pause")]
        static IEnumerator EnPause(Camera camera)
        {
            HorlogeDeCarte h = Lot525.Horloge ?? throw Echec("l'horloge n'a pas été mise en marche : « 01-en-marche » passe avant");
            for (var e = Lot525.EnPause(camera); e.MoveNext();) yield return null;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            string[] lignes = Juger(camera, h, "en pause");
            if (lignes[1] != "En pause") throw Echec("en pause : la seconde ligne dit « " + lignes[1] + " »");
            Button bouton = Cabinet(h).GetComponentsInChildren<Button>(true).FirstOrDefault(b => b.name == "Pause / Reprendre")
                ?? throw Echec("en pause : le bandeau n'a pas de bouton « Pause / Reprendre »");
            Text libelle = bouton.GetComponentInChildren<Text>(true) ?? throw Echec("en pause : le bouton « Pause / Reprendre » n'a pas de libellé");
            if (libelle.text != "Reprendre") throw Echec("en pause : le bouton dit « " + libelle.text + " »");
        }

        static Transform Cabinet(HorlogeDeCarte h) => h.transform.Find("Cabinet") ?? throw Echec("la carte n'a pas de cabinet");

        // Le texte de la date du bandeau, jugé dans l'image où il est lu ; rend ses deux lignes.
        static string[] Juger(Camera camera, HorlogeDeCarte h, string moment)
        {
            Text bandeau = Cabinet(h).GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == "Lecture de la date…")
                ?? throw Echec(moment + " : le cabinet n'a pas de « Lecture de la date… »");
            if (h.Lue == null) throw Echec(moment + " : aucune horloge servie : « " + h.TexteAffiche + " »");
            if (Environment.GetCommandLineArgs().Contains(DRAPEAU_TICK))
                bandeau.text = HorlogeDeCarte.Decrire(h.Lue).Replace("\n", " · tick " + h.Lue.Tick + "\n");
            string texte = bandeau.text, mot = TexteDuMonde.Interdit(texte);
            if (mot != null) throw Echec(moment + " : mot interdit « " + mot + " » dans le bandeau : « " + texte + " »");
            if (texte != h.TexteAffiche || h.TexteAffiche != HorlogeDeCarte.Decrire(h.Lue))
                throw Echec(moment + " : le bandeau dit « " + texte + " », le panneau « " + h.TexteAffiche + " », l'horloge servie « " + HorlogeDeCarte.Decrire(h.Lue) + " »");
            string[] lignes = texte.Split('\n');
            string date = "Jour " + h.Lue.Date.JourDeLAnnee.ToString(CultureInfo.InvariantCulture) + " de " + h.Lue.Date.Annee.ToString(CultureInfo.InvariantCulture);
            if (lignes.Length != 2 || lignes[0] != date) throw Echec(moment + " : la date dit « " + lignes[0] + " », attendu « " + date + " »");
            Lot690.DansLeChamp(camera, bandeau);
            Debug.Log("CAPTURE_883 " + moment + " : " + texte.Replace("\n", " | "));
            return lignes;
        }
    }
}
