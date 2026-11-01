using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Lot 526 : le survol d'une cellule ouvre sa fiche. La carte s'ouvre comme au lot 549, son survol en automatique ; dix
    // crans de molette rapprochent la Lorraine, puis la souris se pose sur le nom de Metz. La fiche doit être celle de la
    // cellule qui porte Metz dans la carte servie, et dire ses habitants et sa faim au tick du monde lu. La photo : la
    // Lorraine de près, avec la fiche en bas à gauche et l'horloge en haut à droite.
    // Lot 929 : le bourg servi au rang 0 de `/lieu` est lu à part ; la fiche doit l'écrire en tête, et parler en noms (`Juger`).
    static class Lot526
    {
        const string VILLE = "Metz";
        const float CRANS = 10f;
        const double ATTENTE_S = 20;
        const int IMAGES_DE_POSE = 10;

        internal static FicheDeCellule Fiche; // posés par le scénario, pour le lot 929
        internal static string Bourg;

        [ScenarioDeCapture(526, "fiche-de-metz")]
        internal static IEnumerator FicheDeMetz(Camera camera)
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
            Fiche = fiche; Bourg = null;
            // Lot #929 : le bourg servi au rang 0 de `/lieu`, lu à part ; la fiche doit finir par l'écrire.
            Task<LectureLieu> lieu = Task.Run(() => { using (var c = new ClientLieu(fiche.port, TimeSpan.FromSeconds(ATTENTE_S))) return c.Lire(cellule.CellId); });
            for (var e = Lot690.Attendre(lieu, "lecture /lieu?cell=" + cellule.CellId); e.MoveNext();) yield return null;
            if (!lieu.Result.Presente) throw new InvalidOperationException("/lieu?cell=" + cellule.CellId + " absent : " + lieu.Result.Absence);
            Bourg = lieu.Result.Lieu.Bourg?.Nom
                ?? throw new InvalidOperationException("/lieu?cell=" + cellule.CellId + " sans nom au rang 0 : " + (lieu.Result.Lieu.Bourg?.AbsenceDuNom ?? "aucun lieu de rang 0"));
            fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (fiche.NomDuBourg != Bourg)
            {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException("la fiche n'écrit pas « " + Bourg + " » en " + ATTENTE_S + " s : « " + fiche.TexteAffiche + " »");
                yield return null;
            }
            Juger(fiche, Bourg);

            Lot549.Photographier(camera, carte);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Debug.Log("CAPTURE_526 " + fiche.TexteAffiche.Replace("\n", " | "));
        }

        // Lot #929 : la fiche affichée parle en noms. Ni mot interdit ni identifiant, aucun nombre sans unité, le texte même
        // de `Decrire` avec le bourg servi, ce bourg en tête, et les habitants de la terre au jour du monde lu.
        internal static void Juger(FicheDeCellule fiche, string bourg)
        {
            string texte = fiche.TexteAffiche ?? throw new InvalidOperationException("la fiche n'est pas affichée");
            CelluleDeCarte cellule = fiche.Survolee ?? throw new InvalidOperationException("aucune terre survolée");
            string id = cellule.CellId.ToString(CultureInfo.InvariantCulture);
            string mot = TexteDuMonde.Interdit(texte, id);
            if (mot != null) throw new InvalidOperationException("mot interdit « " + mot + " » dans la fiche : « " + texte + " »");
            string nu = TexteDuMonde.SansUnite(texte);
            if (nu != null) throw new InvalidOperationException("nombre sans unité « " + nu + " » dans la fiche : « " + texte + " »");
            MondeLu monde = fiche.MondeLu ?? throw new InvalidOperationException("la fiche n'a pas lu le monde : « " + texte + " »");
            if (texte != FicheDeCellule.Decrire(cellule, Lecture<MondeLu>.De(monde), bourg))
                throw new InvalidOperationException("la fiche dit « " + texte + " »");
            if (!texte.Split('\n')[0].StartsWith(bourg, StringComparison.Ordinal))
                throw new InvalidOperationException("la fiche ne commence pas par « " + bourg + " » : « " + texte + " »");
            var vivante = monde.Cellules.FirstOrDefault(c => c.CellId == cellule.CellId)
                ?? throw new InvalidOperationException("la terre de « " + bourg + " » est absente du monde servi");
            string habitants = "\nHabitants : " + TexteDuMonde.Nombre(vivante.Population) + (vivante.Population == 0 || vivante.Population == 1 ? " habitant" : " habitants")
                + " · " + TexteDuMonde.Date(monde.Date);
            if (!texte.Contains(habitants)) throw new InvalidOperationException("la fiche ne dit pas « " + habitants.Trim() + " » : « " + texte + " »");
        }
    }
}
