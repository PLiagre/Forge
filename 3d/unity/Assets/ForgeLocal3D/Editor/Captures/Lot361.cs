using System;
using System.Collections;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 361 : la capitale ouverte d'après le plan. La capture tourne avec le service de `sim/` sur le
    // port 8000, à vitesse 0 : on dépose au monde la route de plaine et la route trop raide du jeu de
    // gestes, sans l'essai du relief, on fait passer un tick, puis l'outil rouvre la ville comme au
    // lancement. La photo montre la rue de terre battue sur le sable, et le panneau qui nomme la rue
    // raide refusée par le relief. Le plan fixe, pris avant, montre le sable vierge.
    static class Lot361
    {
        const float INCLINAISON = 60f;
        const float DISTANCE_M = 90f;
        const int IMAGES_DE_POSE = 10;
        const int DELAI_S = 60;

        // Point du repère de paysage.py vers le monde d'Unity (comme DesertCityRoads.World).
        static Vector3 Monde(Terrain t, double x, double y)
        {
            var p = new Vector3((float)-x, 0, (float)-y);
            p.y = t.SampleHeight(p) + t.transform.position.y;
            return p;
        }

        // La dernière rue du plan aux points et à la largeur du geste : celle que ce scénario vient de déposer.
        static long Identifiant(PlanLu plan, DesertRoads.Geste g)
        {
            var rue = plan.Rues.LastOrDefault(u => u.LargeurM == g.largeur && u.Points.Count == g.x.Length
                && Enumerable.Range(0, g.x.Length).All(i => Math.Abs(u.Points[i].X - g.x[i]) < 1e-6 && Math.Abs(u.Points[i].Y - g.y[i]) < 1e-6));
            if (rue == null)
                throw new InvalidOperationException("la route " + g.id + " n'est pas au plan du tick " + plan.Tick);
            return rue.Identifiant;
        }

        [ScenarioDeCapture(361, "ouverture")]
        static IEnumerator Ouverture(Camera camera)
        {
            var outil = Object.FindFirstObjectByType<DesertRoadTool>();
            var ville = Object.FindFirstObjectByType<DesertCityCamera>();
            if (outil == null || ville == null)
                throw new InvalidOperationException("la scène n'a pas d'outil des routes ou de DesertCityCamera");
            outil.automatique = true;
            var roads = outil.roads;
            var gestes = DesertRoads.Lire(roads.implantation).routes;
            var plaine = gestes.FirstOrDefault(g => g.famille == "plaine");
            var raide = gestes.FirstOrDefault(g => g.famille == "raide_long");
            if (plaine == null || raide == null)
                throw new InvalidOperationException("le jeu de gestes de " + roads.implantation + " n'a pas de route de plaine ou de route raide_long");

            // Les dépôts et le tick, hors du fil de l'éditeur : y attendre HttpClient peut ne jamais revenir.
            int port = outil.Port;
            long cellule = outil.Cellule;
            var intentions = new[] { outil.Intention(plaine), outil.Intention(raide) };
            var recus = Task.Run(() =>
            {
                using (var depot = new ClientIntention(port, TimeSpan.FromSeconds(DELAI_S)))
                    return intentions.Select(depot.Deposer).ToArray();
            }).GetAwaiter().GetResult();
            for (int i = 0; i < recus.Length; i++)
                if (!recus[i].Acceptee)
                    throw new InvalidOperationException("la route " + (i == 0 ? plaine.id : raide.id) + " n'est pas acceptée par le monde : "
                        + (recus[i].Presente ? recus[i].Erreur : recus[i].Absence));
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
            var lu = Task.Run(() =>
            {
                using (var plan = new ClientPlan(port, TimeSpan.FromSeconds(DELAI_S)))
                    return plan.Lire(cellule);
            }).GetAwaiter().GetResult();
            if (!lu.Presente)
                throw new InvalidOperationException("pas de plan après le tick : " + lu.Absence);
            long idPlaine = Identifiant(lu.Plan, plaine), idRaide = Identifiant(lu.Plan, raide);

            // Le code même que le Start de la scène joue au lancement.
            if (!outil.Ouvrir())
                throw new InvalidOperationException("l'outil n'a pas ouvert la ville : " + outil.Message);
            if (!outil.Ouverture.Any(e => e.identifiant == idPlaine && e.resultat.acceptee))
                throw new InvalidOperationException("la rue de plaine " + idPlaine + " n'est pas posée à l'ouverture : " + outil.Message);
            if (!outil.Ouverture.Any(e => e.identifiant == idRaide && !e.resultat.acceptee))
                throw new InvalidOperationException("la rue raide " + idRaide + " n'est pas refusée à l'ouverture : " + outil.Message);
            if (!outil.Message.Contains("Rue " + idRaide + " refusée par le relief"))
                throw new InvalidOperationException("le panneau ne nomme pas la rue raide refusée : " + outil.Message);

            int q = plaine.x.Length / 2;
            ville.Poser(Monde(roads.terrain, plaine.x[q], plaine.y[q]), ville.Cap, INCLINAISON, DISTANCE_M);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }
    }
}
