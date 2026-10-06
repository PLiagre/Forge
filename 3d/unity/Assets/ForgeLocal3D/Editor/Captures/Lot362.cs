using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 362 : la ville dessine les parcelles du plan. La capture tourne avec le service de `sim/` sur le
    // port 8000, à vitesse 0 : on dépose au monde la route de plaine du jeu de gestes, un tick la met au
    // plan, puis on y découpe deux parcelles côte à côte (segments 3 et 4, à gauche), et deux ticks
    // achèvent la première, à 100 foyers, quand la seconde reste en chantier. L'outil rouvre alors la
    // ville comme au lancement. La photo montre la rue de terre battue, la parcelle achevée cernée de
    // chaux et ses bornes blanches, la parcelle en chantier et son cordeau sur quatre piquets. Le plan
    // fixe, pris avant, montre le sable vierge.
    static class Lot362
    {
        const float INCLINAISON = 50f;
        const float DISTANCE_M = 35f;
        const int IMAGES_DE_POSE = 10;
        const int DELAI_S = 60;

        // Point du repère de paysage.py vers le monde d'Unity (comme DesertCityRoads.World).
        internal static Vector3 Monde(Terrain t, double x, double y)
        {
            var p = new Vector3((float)-x, 0, (float)-y);
            p.y = t.SampleHeight(p) + t.transform.position.y;
            return p;
        }

        // La dernière rue du plan aux points et à la largeur du geste : celle que ce scénario vient de déposer.
        internal static long Identifiant(PlanLu plan, DesertRoads.Geste g)
        {
            var rue = plan.Rues.LastOrDefault(u => u.LargeurM == g.largeur && u.Points.Count == g.x.Length
                && Enumerable.Range(0, g.x.Length).All(i => Math.Abs(u.Points[i].X - g.x[i]) < 1e-6 && Math.Abs(u.Points[i].Y - g.y[i]) < 1e-6));
            if (rue == null)
                throw new InvalidOperationException("la route " + g.id + " n'est pas au plan du tick " + plan.Tick);
            return rue.Identifiant;
        }

        // Les dépôts, hors du fil de l'éditeur : y attendre HttpClient peut ne jamais revenir.
        internal static void Deposer(int port, params string[] intentions)
        {
            var recus = Task.Run(() =>
            {
                using (var depot = new ClientIntention(port, TimeSpan.FromSeconds(DELAI_S)))
                    return intentions.Select(depot.Deposer).ToArray();
            }).GetAwaiter().GetResult();
            for (int i = 0; i < recus.Length; i++)
                if (!recus[i].Acceptee)
                    throw new InvalidOperationException("l'intention " + intentions[i] + " n'est pas acceptée par le monde : "
                        + (recus[i].Presente ? recus[i].Erreur : recus[i].Absence));
        }

        internal static void Tick(int port)
        {
            string url = "http://127.0.0.1:" + port + "/tick?n=1";
            int statut = Task.Run(() =>
            {
                using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(DELAI_S) })
                using (var corps = new ByteArrayContent(new byte[0]))
                using (var reponse = http.PostAsync(url, corps).GetAwaiter().GetResult())
                    return (int)reponse.StatusCode;
            }).GetAwaiter().GetResult();
            if (statut != 200)
                throw new InvalidOperationException("POST " + url + " a rendu " + statut);
        }

        internal static PlanLu Lire(int port, long cellule)
        {
            var lu = Task.Run(() =>
            {
                using (var plan = new ClientPlan(port, TimeSpan.FromSeconds(DELAI_S)))
                    return plan.Lire(cellule);
            }).GetAwaiter().GetResult();
            if (!lu.Presente)
                throw new InvalidOperationException("pas de plan : " + lu.Absence);
            return lu.Plan;
        }

        [ScenarioDeCapture(362, "parcelles")]
        static IEnumerator Parcelles(Camera camera)
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
            Deposer(port, outil.Intention(plaine));
            Tick(port);
            var plan = Lire(port, cellule);
            long rue = Identifiant(plan, plaine);
            int n0 = plan.Parcelles.Count;

            // Les deux découpes de la session tracer de DesertCityRelance.
            string decoupe = "{\"type\":\"decouper_parcelle\",\"cell\":" + cellule.ToString(CultureInfo.InvariantCulture)
                + ",\"rue\":" + rue.ToString(CultureInfo.InvariantCulture) + ",\"segment\":";
            const string MESURES = ",\"debut_m\":1,\"facade_m\":8,\"profondeur_m\":15,\"cote\":\"gauche\"";
            Deposer(port, decoupe + "3" + MESURES + ",\"foyers\":100}", decoupe + "4" + MESURES + "}");
            Tick(port);
            Tick(port);

            // Le code même que le Start de la scène joue au lancement.
            if (!outil.Ouvrir())
                throw new InvalidOperationException("l'outil n'a pas ouvert la ville : " + outil.Message);
            if (outil.Parcelles.Count < n0 + 2 || outil.Parcelles[n0].etat != "bornes" || outil.Parcelles[n0 + 1].etat != "cordeau")
                throw new InvalidOperationException("les parcelles découpées ne sont pas dessinées achevée puis en chantier : "
                    + string.Join(", ", outil.Parcelles.Select(p => p.identifiant + " " + p.etat)) + " (" + outil.Message + ")");
            if (!outil.Message.Split('\n').Any(l => l.StartsWith("Parcelles : ", StringComparison.Ordinal)))
                throw new InvalidOperationException("le panneau ne compte pas les parcelles : " + outil.Message);

            // Le centre des huit coins des deux parcelles, relus au plan.
            plan = Lire(port, cellule);
            if (plan.Parcelles.Count < n0 + 2)
                throw new InvalidOperationException("le plan du tick " + plan.Tick + " compte " + plan.Parcelles.Count + " parcelle(s), il en faut " + (n0 + 2));
            var coins = plan.Parcelles.Skip(n0).Take(2).SelectMany(p => p.Contour).Select(c => Monde(roads.terrain, c.X, c.Y)).ToArray();
            var centre = coins.Aggregate(Vector3.zero, (s, c) => s + c) / coins.Length;
            ville.Poser(centre, ville.Cap, INCLINAISON, DISTANCE_M);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }
    }
}
