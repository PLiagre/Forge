using System;
using System.Collections;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 929 : la fiche de survol parle en noms. La Lorraine de près, comme au lot 526 ; la fiche de la terre de Metz,
    // en bas à gauche, commence par le bourg servi (« Metz »), puis sa puissance, sa maison, ses habitants au jour du
    // monde, sa faim en jours et sa dette en masse. Ni tick ni identifiant. `-forge929Cabinet` est la contre-épreuve :
    // la fiche reçoit le texte du cabinet (`Decrire` à deux arguments), et le juge du lot 526 doit la refuser.
    static class Lot929
    {
        const string CABINET = "-forge929Cabinet";

        [ScenarioDeCapture(929, "fiche-de-metz")]
        static IEnumerator FicheDeMetz(Camera camera)
        {
            for (var e = Lot526.FicheDeMetz(camera); e.MoveNext();) yield return null;
            FicheDeCellule fiche = Lot526.Fiche ?? throw new InvalidOperationException("le lot 526 n'a pas posé de fiche");
            // Sous le cabinet, la toile de la fiche s'éteint à chaque image et la caméra ne prend que l'ouest de l'écran :
            // la photo la rallume, sans attendre d'image, et la caméra prend toute l'image, décalée vers l'est pour garder la
            // carte à sa place (comme au lot 730). La toile du cabinet reste en overlay, hors de la photo.
            Transform toile = fiche.transform.Find("Toile de la fiche") ?? throw new InvalidOperationException("la fiche n'a pas de toile");
            float largeur = camera.rect.width; camera.rect = new Rect(0, 0, 1, 1);
            camera.transform.position += camera.transform.right * (1 - largeur) * camera.orthographicSize * camera.aspect;
            toile.gameObject.SetActive(true);
            if (toile.GetComponent<Canvas>().worldCamera != camera) throw new InvalidOperationException("la toile de la fiche ne se dessine pas sur la caméra photographiée");
            if (Environment.GetCommandLineArgs().Contains(CABINET))
            {
                Text texte = fiche.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.text == fiche.TexteAffiche)
                    ?? throw new InvalidOperationException("aucun texte ne porte la fiche « " + fiche.TexteAffiche + " »");
                texte.text = FicheDeCellule.Decrire(fiche.Survolee, Lecture<MondeLu>.De(fiche.MondeLu));
            }
            Canvas.ForceUpdateCanvases();
            // Sans attendre d'image : la fiche jugée est celle que `Capture.Photographier` prend après la fin du scénario.
            Lot526.Juger(fiche, Lot526.Bourg);
            if (Lot526.Bourg != "Metz") throw new InvalidOperationException("le bourg servi de la terre de Metz est « " + Lot526.Bourg + " »");
            Debug.Log("CAPTURE_929 " + fiche.TexteAffiche.Replace("\n", " | "));
        }
    }
}
