using System;
using System.Collections;
using System.Linq;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Lot 526 : le survol d'une cellule ouvre sa fiche. La carte s'ouvre comme au lot 549, son survol en automatique ; dix
    // crans de molette rapprochent la Lorraine, puis la souris se pose sur le nom de Metz. La fiche doit être celle de la
    // cellule qui porte Metz dans la carte servie, et dire ses habitants et sa faim au tick du monde lu. La photo : la
    // Lorraine de près, avec la fiche en bas à gauche et l'horloge en haut à droite.
    static class Lot526
    {
        const string VILLE = "Metz";
        const float CRANS = 10f;
        const double ATTENTE_S = 20;
        const int IMAGES_DE_POSE = 10;

        [ScenarioDeCapture(526, "fiche-de-metz")]
        static IEnumerator FicheDeMetz(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            var carte = ouverte.Carte;
            var fiche = carte.GetComponent<FicheDeCellule>() ?? throw new InvalidOperationException("la carte n'a pas de fiche de cellule");
            (carte.GetComponent<SurvolDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas de survol")).automatique = true;
            (carte.GetComponent<ParcoursDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas de parcours")).automatique = true;
            var nom = carte.GetComponentsInChildren<TextMesh>().FirstOrDefault(t => t.text == VILLE)
                ?? throw new InvalidOperationException("pas de nom « " + VILLE + " » sur la carte");

            carte.Vue.Zoomer(CRANS, carte.camera.WorldToViewportPoint(nom.transform.position));
            yield return null; // la carte pose sa caméra sur la vue
            fiche.Survoler(carte.camera.WorldToScreenPoint(nom.transform.position));
            var cellule = fiche.Survolee ?? throw new InvalidOperationException("sous le nom de " + VILLE + ", aucune cellule");
            if (!cellule.Villes.Any(v => v.Nom == VILLE))
                throw new InvalidOperationException("sous le nom de " + VILLE + ", la cellule " + cellule.CellId + " ne porte pas " + VILLE);

            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (fiche.MondeLu == null)
            {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException("pas de monde lu en " + ATTENTE_S + " s : « " + fiche.TexteAffiche + " »");
                yield return null;
            }
            fiche.Survoler(carte.camera.WorldToScreenPoint(nom.transform.position));
            var vivante = fiche.MondeLu.Cellules.FirstOrDefault(c => c.CellId == cellule.CellId)
                ?? throw new InvalidOperationException("la cellule " + cellule.CellId + " est absente du monde servi");
            string attendue = FicheDeCellule.Decrire(cellule, Lecture<MondeLu>.De(fiche.MondeLu));
            if (fiche.TexteAffiche != attendue || !attendue.Contains("\nHabitants : " + vivante.Population + " au tick " + fiche.MondeLu.Tick))
                throw new InvalidOperationException("la fiche dit « " + fiche.TexteAffiche + " »");

            Lot549.Photographier(camera, carte);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Debug.Log("CAPTURE_526 " + fiche.TexteAffiche.Replace("\n", " | "));
        }
    }
}
