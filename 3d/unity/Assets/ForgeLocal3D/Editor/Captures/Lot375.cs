using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 375 : le joueur trace une parcelle dans la 3D. La capture tourne avec le service de `sim/` sur le
    // port 8000, à vitesse 0 : on dépose la route de plaine du jeu de gestes, un tick la met au plan, l'outil
    // rouvre la ville. Puis, par le geste du joueur (P, deux clics, Entrée), une parcelle de 8 m × 15 m à
    // gauche du segment 5 : le monde l'accepte, et au tick suivant l'outil la dessine au cordeau. Une seconde,
    // sur le segment 7, déborde du segment : l'outil la refuse, et rien n'atteint le monde. La photo montre la
    // rue de terre battue, la parcelle en chantier et son cordeau, et le panneau qui dit le refus. Le plan
    // fixe, pris avant, montre le sable vierge. Tout appel direct au service passe par les aides de Lot362.
    static class Lot375
    {
        const float INCLINAISON = 50f;
        const float DISTANCE_M = 35f;
        // Les clics se font de haut, sur une image de la taille de la photo.
        const float INCLINAISON_CLIC = 85f;
        const float DISTANCE_CLIC_M = 60f;
        const int IMAGES_DE_POSE = 10;
        const double TOLERANCE_M = .05;

        // Le point à `s` m le long du segment `i` de la rue et à `h` m à sa gauche (normale (−u_y, u_x)).
        internal static (double x, double y) Point(RueDuPlan rue, int i, double s, double h)
        {
            PointLocal a = rue.Points[i], b = rue.Points[i + 1];
            double dx = b.X - a.X, dy = b.Y - a.Y, l = Math.Sqrt(dx * dx + dy * dy);
            double ux = dx / l, uy = dy / l;
            return (a.X + s * ux - h * uy, a.Y + s * uy + h * ux);
        }

        internal static Vector3 Milieu(Terrain t, RueDuPlan rue, int i) =>
            Lot362.Monde(t, (rue.Points[i].X + rue.Points[i + 1].X) / 2, (rue.Points[i].Y + rue.Points[i + 1].Y) / 2);

        // Vise de haut `vise`, puis clique chaque point avec l'outil du joueur. La caméra est rendue ensuite.
        internal static void Cliquer(Camera camera, DesertCityCamera ville, DesertRoadTool outil, Vector3 vise, params (double x, double y)[] points)
        {
            var rt = new RenderTexture(1600, 900, 24);
            camera.targetTexture = rt;
            try
            {
                ville.Poser(vise, ville.Cap, INCLINAISON_CLIC, DISTANCE_CLIC_M);
                foreach (var p in points)
                    if (!outil.Clic(camera.WorldToScreenPoint(Lot362.Monde(outil.roads.terrain, p.x, p.y))))
                        throw new InvalidOperationException("le clic en (" + p.x.ToString("R", CultureInfo.InvariantCulture) + " ; "
                            + p.y.ToString("R", CultureInfo.InvariantCulture) + ") n'est pas passé par l'outil : " + outil.Message);
            }
            finally
            {
                camera.targetTexture = null;
                rt.Release();
                Object.DestroyImmediate(rt);
            }
        }

        static bool Proche(double mesure, double attendue) => Math.Abs(mesure - attendue) < TOLERANCE_M;

        [ScenarioDeCapture(375, "parcelle-tracee")]
        static IEnumerator Tracer(Camera camera)
        {
            var outil = Object.FindFirstObjectByType<DesertRoadTool>();
            var ville = Object.FindFirstObjectByType<DesertCityCamera>();
            if (outil == null || ville == null)
                throw new InvalidOperationException("la scène n'a pas d'outil des routes ou de DesertCityCamera");
            outil.automatique = true;
            var roads = outil.roads;
            var plaine = DesertRoads.Lire(roads.implantation).routes.FirstOrDefault(g => g.famille == "plaine");
            if (plaine == null)
                throw new InvalidOperationException("le jeu de gestes de " + roads.implantation + " n'a pas de route de plaine");

            int port = outil.Port;
            long cellule = outil.Cellule;
            Lot362.Deposer(port, outil.Intention(plaine));
            Lot362.Tick(port);
            var plan = Lot362.Lire(port, cellule);
            long identifiant = Lot362.Identifiant(plan, plaine);
            int n0 = plan.Parcelles.Count;
            if (!outil.Ouvrir())
                throw new InvalidOperationException("l'outil n'a pas ouvert la ville : " + outil.Message);
            var terrain = roads.terrain;
            var rue = plan.Rues.First(u => u.Identifiant == identifiant);

            // Échap ramène au mode route, même avec un coin posé.
            outil.EntrerParcelle();
            Cliquer(camera, ville, outil, Milieu(terrain, rue, 5), Point(rue, 5, 4, 3));
            outil.Annuler();
            if (outil.ModeParcelle)
                throw new InvalidOperationException("Échap n'a pas ramené l'outil au mode route : " + outil.Message);

            // La première parcelle, par le geste : 1 m après le début du segment 5, 8 m de façade, 15 m de profondeur
            // au-delà de la demi-chaussée de 2 m.
            plan = Lot362.Lire(port, cellule);
            rue = plan.Rues.First(u => u.Identifiant == identifiant);
            outil.EntrerParcelle();
            Cliquer(camera, ville, outil, Milieu(terrain, rue, 5), Point(rue, 5, 1, 3), Point(rue, 5, 9, 17));
            var tracee = outil.ValiderParcelle();
            if (tracee == null || tracee != outil.Tracee || !tracee.Presente)
                throw new InvalidOperationException("l'outil n'a pas tracé la première parcelle : " + outil.Message);
            if (tracee.Rue != identifiant || tracee.Segment != 5 || tracee.Cote != "gauche")
                throw new InvalidOperationException("la première parcelle est sur la rue " + tracee.Rue + ", segment " + tracee.Segment + ", côté "
                    + tracee.Cote + " ; il faut la rue " + identifiant + ", segment 5, côté gauche");
            if (!Proche(tracee.DebutM, 1) || !Proche(tracee.FacadeM, 8) || !Proche(tracee.ProfondeurM, 15))
                throw new InvalidOperationException("la première parcelle mesure début " + tracee.DebutM.ToString("R", CultureInfo.InvariantCulture)
                    + ", façade " + tracee.FacadeM.ToString("R", CultureInfo.InvariantCulture) + ", profondeur "
                    + tracee.ProfondeurM.ToString("R", CultureInfo.InvariantCulture) + " ; il faut 1, 8 et 15 m à " + TOLERANCE_M + " m près");
            if (outil.Recu == null || !outil.Recu.Acceptee)
                throw new InvalidOperationException("la première parcelle n'est pas acceptée par le monde : " + outil.Message);
            if (!outil.Message.Split('\n').Any(l => l.StartsWith("Parcelle déposée au monde", StringComparison.Ordinal)))
                throw new InvalidOperationException("le panneau ne dit pas le dépôt : " + outil.Message);
            if (!outil.ModeParcelle)
                throw new InvalidOperationException("l'outil a quitté le mode parcelle après le dépôt");

            // Le tick : la parcelle entre au plan en chantier, l'outil la dessine au cordeau.
            Lot362.Tick(port);
            if (!outil.Attendre())
                throw new InvalidOperationException("après le tick, l'outil n'a pas relu de plan plus récent que son dépôt");
            plan = Lot362.Lire(port, cellule);
            if (plan.Parcelles.Count != n0 + 1 || !plan.Parcelles[n0].EnChantier)
                throw new InvalidOperationException("le plan du tick " + plan.Tick + " compte " + plan.Parcelles.Count + " parcelle(s), il en faut "
                    + (n0 + 1) + " dont la dernière en chantier");
            if (outil.Parcelles.Count != n0 + 1 || outil.Parcelles[n0].etat != "cordeau")
                throw new InvalidOperationException("la parcelle neuve n'est pas dessinée au cordeau : "
                    + string.Join(", ", outil.Parcelles.Select(p => p.identifiant + " " + p.etat)) + " (" + outil.Message + ")");
            if (!outil.Message.Split('\n').Any(l => l.StartsWith("Parcelles : ", StringComparison.Ordinal)))
                throw new InvalidOperationException("le panneau ne compte pas les parcelles : " + outil.Message);

            // La seconde parcelle déborde du segment 7 (5 + 7 m sur moins de 10 m) : l'outil la refuse, le monde n'en sait rien.
            rue = plan.Rues.First(u => u.Identifiant == identifiant);
            Cliquer(camera, ville, outil, Milieu(terrain, rue, 7), Point(rue, 7, 5, 3), Point(rue, 7, 12, 17));
            tracee = outil.ValiderParcelle();
            if (tracee == null || tracee.Presente || !tracee.Absence.StartsWith("façade dépasse le segment", StringComparison.Ordinal))
                throw new InvalidOperationException("la seconde parcelle n'est pas refusée par l'outil pour sa façade : " + outil.Message);
            if (outil.Recu != null)
                throw new InvalidOperationException("la seconde parcelle a atteint le monde : " + outil.Message);
            if (!outil.Message.Split('\n')[0].StartsWith("Parcelle refusée par l'outil : façade dépasse le segment", StringComparison.Ordinal))
                throw new InvalidOperationException("le panneau ne dit pas le refus de l'outil : " + outil.Message);
            Lot362.Tick(port);
            plan = Lot362.Lire(port, cellule);
            if (plan.Parcelles.Count != n0 + 1)
                throw new InvalidOperationException("le plan du tick " + plan.Tick + " compte " + plan.Parcelles.Count + " parcelle(s), il en faut " + (n0 + 1));

            var panneau = outil.view.transform.Find("Panneau des routes")?.GetComponent<TextMesh>();
            if (panneau == null)
                throw new InvalidOperationException("la caméra de l'outil n'a pas de panneau");
            Debug.Log("CAPTURE_375 " + panneau.text.Replace("\n", " | "));

            var coins = plan.Parcelles[n0].Contour.Select(c => Lot362.Monde(terrain, c.X, c.Y)).ToArray();
            var centre = coins.Aggregate(Vector3.zero, (s, c) => s + c) / coins.Length;
            ville.Poser(centre, ville.Cap, INCLINAISON, DISTANCE_M);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }
    }
}
