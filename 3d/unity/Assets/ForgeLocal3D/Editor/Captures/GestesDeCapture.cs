using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Les gestes qu'un scénario de capture ou une épreuve fait au monde et à la ville : déposer une
    // intention, pousser un jour, lire le plan, cliquer avec l'outil du joueur ou presser un bouton au pointeur. Tout appel direct au
    // service de `sim/` passe par ici.
    static class GestesDeCapture
    {
        const int DELAI_S = 60;
        // Les clics se font de haut, sur une image de la taille de la photo.
        const float INCLINAISON_CLIC = 85f;
        const float DISTANCE_CLIC_M = 60f;

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

        // Le point à `s` m le long du segment `i` de la rue et à `h` m à sa gauche (normale (−u_y, u_x)).
        internal static (double x, double y) Point(RueDuPlan rue, int i, double s, double h)
        {
            PointLocal a = rue.Points[i], b = rue.Points[i + 1];
            double dx = b.X - a.X, dy = b.Y - a.Y, l = Math.Sqrt(dx * dx + dy * dy);
            double ux = dx / l, uy = dy / l;
            return (a.X + s * ux - h * uy, a.Y + s * uy + h * ux);
        }

        internal static Vector3 Milieu(Terrain t, RueDuPlan rue, int i) =>
            Monde(t, (rue.Points[i].X + rue.Points[i + 1].X) / 2, (rue.Points[i].Y + rue.Points[i + 1].Y) / 2);

        // Un clic de pointeur au centre du bouton, tel que l'écran le montre sous `camera` (celle sur laquelle la toile est posée) : ce
        // qui est sous le pointeur reçoit le clic, et ce doit être le bouton, actif.
        internal static void CliquerAuPointeur(Camera camera, Button bouton)
        {
            var systeme = EventSystem.current ?? Object.FindFirstObjectByType<EventSystem>() ?? throw new InvalidOperationException("aucun système d'événements dans la scène");
            Canvas.ForceUpdateCanvases();
            var coins = new Vector3[4]; ((RectTransform)bouton.transform).GetWorldCorners(coins);
            Vector2 ici = RectTransformUtility.WorldToScreenPoint(camera, (coins[0] + coins[2]) / 2f);
            var pointeur = new PointerEventData(systeme) { position = ici, button = PointerEventData.InputButton.Left };
            var touches = new List<RaycastResult>(); systeme.RaycastAll(pointeur, touches);
            if (touches.Count == 0) throw new InvalidOperationException("rien sous le pointeur en " + ici + " pour « " + bouton.name + " »");
            GameObject sous = ExecuteEvents.GetEventHandler<IPointerClickHandler>(touches[0].gameObject);
            if (sous != bouton.gameObject) throw new InvalidOperationException("sous le pointeur en " + ici + " : « " + (sous != null ? sous.name : touches[0].gameObject.name) + " », et non « " + bouton.name + " »");
            if (!bouton.interactable) throw new InvalidOperationException("« " + bouton.name + " » est inactif");
            pointeur.pointerCurrentRaycast = pointeur.pointerPressRaycast = touches[0]; pointeur.pointerPress = sous; pointeur.rawPointerPress = touches[0].gameObject;
            ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerEnterHandler); ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerDownHandler);
            ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerUpHandler); ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerClickHandler);
            ExecuteEvents.Execute(sous, pointeur, ExecuteEvents.pointerExitHandler);
        }

        // Vise de haut `vise`, puis clique chaque point avec l'outil du joueur. La caméra est rendue ensuite.
        internal static void Cliquer(Camera camera, DesertCityCamera ville, DesertRoadTool outil, Vector3 vise, params (double x, double y)[] points)
        {
            var rt = new RenderTexture(1600, 900, 24);
            camera.targetTexture = rt;
            try
            {
                ville.Poser(vise, ville.Cap, INCLINAISON_CLIC, DISTANCE_CLIC_M);
                foreach (var p in points)
                    if (!outil.Clic(camera.WorldToScreenPoint(Monde(outil.roads.terrain, p.x, p.y))))
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
    }
}
