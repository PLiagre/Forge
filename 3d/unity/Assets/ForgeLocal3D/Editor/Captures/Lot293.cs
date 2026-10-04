using System;
using System.Collections;
using System.Linq;
using System.Net.Http;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 293 : le traceur de route passe par le service. La capture tourne avec le service de `sim/`
    // sur le port 8000, à vitesse 0 : on clique la route de plaine du jeu de gestes avec l'outil du
    // joueur, on la valide (dépôt de l'intention `tracer_route`), on photographie le terrain encore
    // vierge et le reçu ; puis on fait passer un tick, l'outil relit `/plan` et dessine la rue neuve en
    // terre battue, et on photographie la route tracée. Les deux scénarios se suivent (ordre des noms).
    static class Lot293
    {
        const float INCLINAISON = 60f;
        const float DISTANCE_M = 90f;
        const int IMAGES_DE_POSE = 10;
        const int DELAI_TICK_S = 60;

        static DesertRoadTool outil;
        static DesertCityCamera ville;
        static Vector3 milieu;

        // Point du repère de paysage.py vers le monde d'Unity (comme DesertCityRoads.World).
        static Vector3 Monde(Terrain t, double x, double y)
        {
            var p = new Vector3((float)-x, 0, (float)-y);
            p.y = t.SampleHeight(p) + t.transform.position.y;
            return p;
        }

        [ScenarioDeCapture(293, "1-depot")]
        static IEnumerator Depot(Camera camera)
        {
            outil = Object.FindFirstObjectByType<DesertRoadTool>();
            ville = Object.FindFirstObjectByType<DesertCityCamera>();
            if (outil == null || ville == null)
                throw new InvalidOperationException("la scène n'a pas d'outil des routes ou de DesertCityCamera");
            var roads = outil.roads;
            var plaine = DesertRoads.Lire(roads.implantation).routes.FirstOrDefault(g => g.famille == "plaine");
            if (plaine == null)
                throw new InvalidOperationException("le jeu de gestes de " + roads.implantation + " n'a pas de route de plaine");
            // L'outil ne relit plus le plan de lui-même : c'est le scénario qui fait passer le tick.
            outil.automatique = true;
            var terrain = roads.terrain;
            int q = plaine.x.Length / 2;
            milieu = Monde(terrain, plaine.x[q], plaine.y[q]);

            // Les clics à l'écran, vus de haut, sur une image de la taille de la photo.
            var rt = new RenderTexture(1600, 900, 24);
            camera.targetTexture = rt;
            ville.Poser(milieu, ville.Cap, 85f, 160f);
            outil.largeur = plaine.largeur;
            outil.Annuler();
            for (int i = 0; i < plaine.x.Length; i++)
                if (!outil.Clic(camera.WorldToScreenPoint(Monde(terrain, plaine.x[i], plaine.y[i]))))
                    throw new InvalidOperationException("le point " + i + " de la route de plaine n'est pas sur le terrain");
            var essai = outil.Valider();
            camera.targetTexture = null;
            rt.Release();
            Object.DestroyImmediate(rt);
            if (essai == null || !essai.acceptee)
                throw new InvalidOperationException("la route de plaine est refusée par le relief : " + outil.Message);
            if (outil.Recu == null || !outil.Recu.Acceptee)
                throw new InvalidOperationException("la route n'est pas acceptée par le monde : " + outil.Message);

            // Avant le tick, le terrain n'a pas bougé : la photo montre le sable vierge et le reçu.
            ville.Poser(milieu, ville.Cap, INCLINAISON, DISTANCE_M);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }

        [ScenarioDeCapture(293, "2-au-tick")]
        static IEnumerator AuTick(Camera camera)
        {
            if (outil == null || ville == null)
                throw new InvalidOperationException("le scénario « 1-depot » n'a pas joué");
            // Hors du fil de l'éditeur : y attendre HttpClient peut ne jamais revenir.
            string url = "http://127.0.0.1:" + outil.Port + "/tick?n=1";
            int statut = System.Threading.Tasks.Task.Run(() =>
            {
                using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(DELAI_TICK_S) })
                using (var corps = new ByteArrayContent(new byte[0]))
                using (var reponse = http.PostAsync(url, corps).GetAwaiter().GetResult())
                    return (int)reponse.StatusCode;
            }).GetAwaiter().GetResult();
            if (statut != 200)
                throw new InvalidOperationException("POST " + url + " a rendu " + statut);
            if (!outil.Attendre())
                throw new InvalidOperationException("après le tick, l'outil n'a pas relu de plan plus récent que son dépôt");
            if (outil.Posees.Count == 0 || !outil.Posees.All(p => p.resultat.acceptee))
                throw new InvalidOperationException("la rue neuve du plan n'a pas été dessinée : " + outil.Message);
            ville.Poser(milieu, ville.Cap, INCLINAISON, DISTANCE_M);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }
    }
}
