using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 388 : la capitale bâtie et son panneau, la capture du jalon 4 au journal. La capture tourne avec le service
    // de `sim/` sur le port 8000, à vitesse 0. Les gestes sont ceux de la preuve (#386), rejoués par DesertCityPreuve
    // avec l'outil du joueur : la route de plaine, une parcelle de 9 m × 15 m sur son segment 5, une scierie dessus,
    // puis sept ticks. Le chantier avance ensuite, un tick après l'autre, jusqu'à ce que le plan dise la scierie aux
    // murs ; l'outil redessine la ville d'après ce plan, et le panneau du lieu relit le même tick. Deux photos : la
    // capitale vue de haut (la rue, la parcelle à ses bornes, la scierie à ses murs) avec le panneau des foyers par
    // métier, du chantier et du logement ; puis la scierie depuis la rue. Le plan fixe, pris avant, montre le sable vierge.
    static class Lot388
    {
        // Une année de chantier au plus : au-delà, le chantier n'avance pas, et la capture le dit.
        const int TICKS_MAX = 365;
        const int DELAI_PANNEAU_S = 20;
        const float INCLINAISON_ENSEMBLE = 50f;
        const float MARGE_ENSEMBLE = 1.1f;
        const float INCLINAISON_RUE = 30f;
        const float DISTANCE_RUE_M = 32f;
        const int IMAGES_DE_POSE = 10;

        // Ce que la première photo a bâti, pour la seconde : les scénarios d'un lot se jouent dans l'ordre de leur nom,
        // dans le même Play.
        static Vector3 centreScierie;
        static float capScierie = float.NaN;

        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);

        static string Etape(BatimentDuPlan b) =>
            LectureDuBatiment.Etape(b) switch { EtapeDuBatiment.Fini => "fini", EtapeDuBatiment.Murs => "murs", _ => "piquets" };

        [ScenarioDeCapture(388, "capitale-batie")]
        static IEnumerator Capitale(Camera camera)
        {
            capScierie = float.NaN;
            var outil = Object.FindFirstObjectByType<DesertRoadTool>();
            var ville = Object.FindFirstObjectByType<DesertCityCamera>();
            var panneau = Object.FindFirstObjectByType<PanneauLieu>();
            if (outil == null || ville == null || panneau == null)
                throw new InvalidOperationException("la scène n'a pas d'outil des routes, de DesertCityCamera ou de PanneauLieu");
            if (panneau.camera != camera)
                throw new InvalidOperationException("le panneau du lieu s'affiche sur la caméra « " + (panneau.camera ? panneau.camera.name : "aucune")
                    + " », la photo est prise par « " + camera.name + " » : il n'y serait pas");

            // Les gestes de la preuve, par l'outil du joueur. Un défaut de la preuve est un défaut de la photo.
            var preuve = DesertCityPreuve.JouerLesGestes(outil);
            if (preuve.defauts.Length > 0)
                throw new InvalidOperationException("les gestes de la preuve n'ont pas bâti la ville : " + string.Join(" | ", preuve.defauts));
            long rueId = preuve.gestes[0].identifiant, parcelleId = preuve.gestes[1].identifiant, scierieId = preuve.gestes[2].identifiant;

            // Le chantier avance jusqu'à ce que le plan dise la scierie aux murs.
            int port = outil.Port;
            long cellule = outil.Cellule;
            var plan = Lot362.Lire(port, cellule);
            BatimentDuPlan LaScierie(PlanLu p) => p.Batiments.FirstOrDefault(b => b.Identifiant == scierieId)
                ?? throw new InvalidOperationException("le plan du tick " + N(p.Tick) + " n'a plus la scierie " + N(scierieId));
            long tickDebut = plan.Tick;
            while (Etape(LaScierie(plan)) == "piquets")
            {
                if (plan.Tick - tickDebut >= TICKS_MAX)
                {
                    var s = LaScierie(plan);
                    throw new InvalidOperationException("après " + TICKS_MAX + " ticks, la scierie " + N(scierieId) + " est encore aux piquets ("
                        + N(s.TravailFourni) + "/" + N(s.TravailRequis) + " journées) : le chantier n'avance pas");
                }
                Lot362.Tick(port);
                plan = Lot362.Lire(port, cellule);
                yield return null;
            }
            if (!outil.Rafraichir())
                throw new InvalidOperationException("l'outil n'a pas redessiné la ville d'après le plan du tick " + N(plan.Tick) + " : " + outil.Message);

            // La ville dessinée est celle du plan relu : la parcelle à son étape, la scierie à la sienne.
            var scierie = LaScierie(plan);
            var parcelle = plan.Parcelles.FirstOrDefault(p => p.Identifiant == parcelleId)
                ?? throw new InvalidOperationException("le plan du tick " + N(plan.Tick) + " n'a plus la parcelle " + N(parcelleId));
            var rue = plan.Rues.FirstOrDefault(u => u.Identifiant == rueId)
                ?? throw new InvalidOperationException("le plan du tick " + N(plan.Tick) + " n'a plus la rue " + N(rueId));
            string etapeParcelle = parcelle.EnChantier ? "cordeau" : "bornes";
            var dessinParcelle = outil.Parcelles.Where(p => p.identifiant == parcelleId).Select(p => p.etat).ToArray();
            if (dessinParcelle.Length != 1 || dessinParcelle[0] != etapeParcelle)
                throw new InvalidOperationException("la parcelle " + N(parcelleId) + " est dessinée [" + string.Join(", ", dessinParcelle)
                    + "], le plan du tick " + N(plan.Tick) + " la dit " + etapeParcelle);
            var dessinScierie = outil.Batiments.Where(b => b.identifiant == scierieId).Select(b => b.etat).ToArray();
            if (dessinScierie.Length != 1 || dessinScierie[0] != Etape(scierie))
                throw new InvalidOperationException("la scierie " + N(scierieId) + " est dessinée [" + string.Join(", ", dessinScierie) + "], le plan du tick "
                    + N(plan.Tick) + " la dit " + Etape(scierie) + " (" + N(scierie.TravailFourni) + "/" + N(scierie.TravailRequis) + ")");

            // Le panneau du lieu relit le même tick, et dit les foyers par métier, le chantier et le logement.
            string tete = "Cellule " + N(cellule) + " · tick " + N(plan.Tick);
            for (double fin = Time.realtimeSinceStartupAsDouble + DELAI_PANNEAU_S; !AuTick(panneau.TexteAffiche, tete);)
            {
                if (Time.realtimeSinceStartupAsDouble > fin)
                    throw new InvalidOperationException("le panneau n'affiche pas « " + tete + " » : " + panneau.TexteAffiche);
                yield return null;
            }
            string foyers = panneau.TexteFoyers ?? "";
            foreach (string ligne in new[] { "Foyers par métier :", "Au chantier : ", "Logement des artisans : " })
                if (!foyers.Split('\n').Any(l => l.StartsWith(ligne, StringComparison.Ordinal)))
                    throw new InvalidOperationException("le panneau ne dit pas « " + ligne.Trim() + " » : " + foyers);
            Debug.Log("CAPTURE_388 tick " + N(plan.Tick) + " · rue " + N(rueId) + (rue.EnChantier ? " en chantier" : " finie") + " · parcelle " + N(parcelleId)
                + " " + etapeParcelle + " · scierie " + N(scierieId) + " " + Etape(scierie) + " (" + N(scierie.TravailFourni) + "/" + N(scierie.TravailRequis)
                + ") · " + foyers.Replace("\n", " | "));

            // Vue de haut : la rue entière et la parcelle dans le champ, la scierie au milieu de l'image.
            var terrain = outil.roads.terrain;
            var points = rue.Points.Select(p => Lot362.Monde(terrain, p.X, p.Y)).Concat(parcelle.Contour.Select(p => Lot362.Monde(terrain, p.X, p.Y))).ToArray();
            var c = (x: parcelle.Contour.Average(k => k.X), y: parcelle.Contour.Average(k => k.Y));
            centreScierie = Lot362.Monde(terrain, c.x, c.y);
            capScierie = (float)LectureDuBatiment.Poser(scierie).LacetDegres + 180f;
            float rayon = points.Max(p => Vector3.Distance(p, centreScierie));
            // La rue court en travers de l'image (la caméra regarde la façade, qui la borde) : le champ horizontal, sur la photo en 16:9.
            float demiChamp = Camera.VerticalToHorizontalFieldOfView(camera.fieldOfView, 16f / 9f) * .5f * Mathf.Deg2Rad;
            ville.Poser(centreScierie, capScierie, INCLINAISON_ENSEMBLE, MARGE_ENSEMBLE * rayon / Mathf.Tan(demiChamp));
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }

        // La scierie à ses murs, vue depuis la rue, à hauteur de toit ; le panneau reste à l'écran.
        [ScenarioDeCapture(388, "scierie-aux-murs")]
        static IEnumerator Scierie(Camera camera)
        {
            if (float.IsNaN(capScierie))
                throw new InvalidOperationException("la capitale n'a pas été bâtie : le scénario « capitale-batie » passe avant celui-ci");
            var ville = Object.FindFirstObjectByType<DesertCityCamera>()
                ?? throw new InvalidOperationException("la scène n'a pas de DesertCityCamera");
            ville.Poser(centreScierie, capScierie, INCLINAISON_RUE, DISTANCE_RUE_M);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }

        static bool AuTick(string texte, string tete) =>
            texte != null && texte.StartsWith(tete, StringComparison.Ordinal) && (texte.Length == tete.Length || texte[tete.Length] == '\n');
    }
}
