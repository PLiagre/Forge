using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 369 : la ville pose les bâtiments du kit à leur étape. La capture tourne avec le service de `sim/`
    // sur le port 8000, à vitesse 0 : on dépose la route de plaine du jeu de gestes, un tick la met au plan,
    // on y découpe trois parcelles de 10 m × 15 m à gauche (segments 4, 6 et 8), deux ticks les achèvent,
    // puis on y pose une maison, une scierie et un four, à 24, 12 et 1 foyers : trois ticks plus tard, la
    // maison est finie, la scierie aux murs, le four aux piquets. L'outil rouvre alors la ville comme au
    // lancement. La photo montre les trois pièces, façades vers la rue. Le plan fixe, pris avant, montre
    // le sable vierge. Tout appel au service passe par les aides de Lot362 (hors du fil de l'éditeur).
    static class Lot369
    {
        const float INCLINAISON = 35f;
        const float DISTANCE_M = 70f;
        const int IMAGES_DE_POSE = 10;
        static readonly int[] SEGMENTS = { 4, 6, 8 };
        // La contre-épreuve du débordement (façade de 8 m) ne change que FACADE_M.
        const int FACADE_M = 10;
        const int PROFONDEUR_M = 15;
        // Le travail requis et fourni trois ticks après la pose, à 10 m × 15 m.
        const long REQUIS = 300;
        static readonly (string nature, int foyers, long fourni, string etat, EtapeDuBatiment etape)[] ATTENDUS =
        {
            ("maison", 24, 300, "fini", EtapeDuBatiment.Fini),
            ("scierie", 12, 180, "murs", EtapeDuBatiment.Murs),
            ("four", 1, 15, "piquets", EtapeDuBatiment.Piquets),
        };

        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);

        // Les maillages d'une pièce, dans l'ordre de sa hiérarchie, tous LOD compris : une instance garde
        // ceux de son prefab, c'est ce qui dit quelle pièce est réellement posée.
        static Mesh[] Maillages(GameObject go) =>
            go.GetComponentsInChildren<MeshFilter>(true).Select(f => f.sharedMesh).Where(m => m != null).ToArray();

        [ScenarioDeCapture(369, "batiments")]
        static IEnumerator Batiments(Camera camera)
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
            long rue = Lot362.Identifiant(plan, plaine);
            int n0 = plan.Parcelles.Count, b0 = plan.Batiments.Count;

            // Trois parcelles de 10 m × 15 m à gauche de la rue, assez grandes pour toutes les pièces du kit.
            string decoupe = "{\"type\":\"decouper_parcelle\",\"cell\":" + N(cellule) + ",\"rue\":" + N(rue) + ",\"segment\":";
            string mesures = ",\"debut_m\":0,\"facade_m\":" + N(FACADE_M) + ",\"profondeur_m\":" + N(PROFONDEUR_M) + ",\"cote\":\"gauche\",\"foyers\":100}";
            Lot362.Deposer(port, SEGMENTS.Select(s => decoupe + s.ToString(CultureInfo.InvariantCulture) + mesures).ToArray());
            Lot362.Tick(port);
            Lot362.Tick(port);
            plan = Lot362.Lire(port, cellule);
            if (plan.Parcelles.Count < n0 + 3 || plan.Parcelles.Skip(n0).Take(3).Any(p => p.EnChantier))
                throw new InvalidOperationException("les trois parcelles découpées ne sont pas achevées au plan du tick " + plan.Tick + " : "
                    + string.Join(", ", plan.Parcelles.Skip(n0).Select(p => p.Identifiant + " " + p.TravailFourni + "/" + p.TravailRequis)));

            Lot362.Deposer(port, Enumerable.Range(0, 3).Select(i => "{\"type\":\"poser_batiment\",\"cell\":" + N(cellule)
                + ",\"parcelle\":" + N(plan.Parcelles[n0 + i].Identifiant) + ",\"nature\":\"" + ATTENDUS[i].nature
                + "\",\"foyers\":" + ATTENDUS[i].foyers.ToString(CultureInfo.InvariantCulture) + "}").ToArray());
            Lot362.Tick(port);
            Lot362.Tick(port);
            Lot362.Tick(port);

            plan = Lot362.Lire(port, cellule);
            if (plan.Batiments.Count < b0 + 3)
                throw new InvalidOperationException("le plan du tick " + plan.Tick + " compte " + plan.Batiments.Count + " bâtiment(s), il en faut " + (b0 + 3));
            var poses = plan.Batiments.Skip(b0).Take(3).ToArray();

            // Les pièces attendues, lues au kit par l'étape voulue, indépendamment de ce que Dessiner a choisi.
            var kit = KitDesBatiments.Charger();
            if (!kit)
                throw new InvalidOperationException("pas de kit des bâtiments (Resources/KitDesBatiments)");
            var prefabs = new GameObject[3];
            for (int i = 0; i < 3; i++)
            {
                var attendue = kit.Piece(ATTENDUS[i].nature, ATTENDUS[i].etape);
                if (!attendue.Presente)
                    throw new InvalidOperationException("le kit n'a pas la pièce attendue : " + attendue.Absence);
                prefabs[i] = attendue.Prefab;
                if (Maillages(prefabs[i]).Length == 0)
                    throw new InvalidOperationException(prefabs[i].name + " n'a aucun maillage à comparer");
                // Sans quoi la comparaison des maillages ne distinguerait pas les étapes de cette nature.
                foreach (EtapeDuBatiment autre in Enum.GetValues(typeof(EtapeDuBatiment)))
                {
                    var p = kit.Piece(ATTENDUS[i].nature, autre);
                    if (autre != ATTENDUS[i].etape && p.Presente && Maillages(p.Prefab).SequenceEqual(Maillages(prefabs[i])))
                        throw new InvalidOperationException(p.Prefab.name + " a les mêmes maillages que " + prefabs[i].name);
                }
            }

            // Le code même que le Start de la scène joue au lancement. La vue est jugée avant les nombres du plan :
            // une pièce refusée (par exemple qui déborde d'une façade de 8 m) se lit ainsi au panneau, même
            // quand le travail requis n'est plus celui de 10 m × 15 m.
            if (!outil.Ouvrir())
                throw new InvalidOperationException("l'outil n'a pas ouvert la ville : " + outil.Message);
            var etats = outil.Batiments.Skip(Math.Max(0, outil.Batiments.Count - 3)).Select(e => e.etat).ToArray();
            if (!etats.SequenceEqual(ATTENDUS.Select(a => a.etat)))
                throw new InvalidOperationException("les bâtiments ne sont pas dessinés fini, murs, piquets : "
                    + string.Join(", ", outil.Batiments.Select(e => e.identifiant + " " + e.etat)) + " (" + outil.Message + ")");
            if (!outil.Message.Split('\n').Any(l => l.StartsWith("Bâtiments : ", StringComparison.Ordinal)))
                throw new InvalidOperationException("le panneau ne compte pas les bâtiments : " + outil.Message);
            for (int i = 0; i < 3; i++)
            {
                var b = poses[i];
                var a = ATTENDUS[i];
                if (b.Nature != a.nature || b.TravailFourni != a.fourni || b.TravailRequis != REQUIS || b.EnChantier != (a.fourni < REQUIS))
                    throw new InvalidOperationException("le bâtiment " + b.Identifiant + " est " + b.Nature + " à " + b.TravailFourni + "/" + b.TravailRequis
                        + (b.EnChantier ? " en chantier" : " achevé") + ", il faut " + a.nature + " à " + a.fourni + "/" + REQUIS);
            }
            var racine = outil.RacineBatiments;
            int posees = outil.Batiments.Count(e => e.etat != "refusee");
            if (racine.childCount != posees)
                throw new InvalidOperationException("la racine des bâtiments a " + racine.childCount + " enfant(s) pour " + posees + " pièce(s) posée(s)");
            for (int i = 0; i < 3; i++)
            {
                var b = poses[i];
                var piece = racine.Find("Bâtiment " + N(b.Identifiant));
                if (piece == null)
                    throw new InvalidOperationException("pas d'enfant « Bâtiment " + b.Identifiant + " » sous la racine des bâtiments");
                if (!Maillages(piece.gameObject).SequenceEqual(Maillages(prefabs[i])))
                    throw new InvalidOperationException("le bâtiment " + b.Identifiant + " n'a pas les maillages de " + prefabs[i].name
                        + " : " + string.Join(", ", Maillages(piece.gameObject).Select(m => m.name)));
                var pose = LectureDuBatiment.Poser(b);
                float ecart = new Vector2(piece.position.x - (float)-pose.CentreX, piece.position.z - (float)-pose.CentreY).magnitude;
                if (ecart >= .01f)
                    throw new InvalidOperationException("le bâtiment " + b.Identifiant + " est à " + ecart.ToString("F3", CultureInfo.InvariantCulture) + " m de son centre");
                var avant = piece.forward;
                avant.y = 0;
                avant.Normalize();
                float alignement = Vector3.Dot(avant, new Vector3((float)-pose.FacadeX, 0, (float)-pose.FacadeY));
                if (!(alignement > .99f))
                    throw new InvalidOperationException("la façade du bâtiment " + b.Identifiant + " ne regarde pas la rue (produit scalaire "
                        + alignement.ToString("F3", CultureInfo.InvariantCulture) + ")");
            }

            // Relancé, Unity repose les mêmes pièces.
            string empreinte = outil.EmpreinteBatiments;
            int enfants = racine.childCount;
            if (!outil.Rafraichir())
                throw new InvalidOperationException("l'outil n'a pas rafraîchi la ville : " + outil.Message);
            if (outil.EmpreinteBatiments != empreinte || racine.childCount != enfants)
                throw new InvalidOperationException("Rafraichir ne repose pas les mêmes pièces : empreinte " + outil.EmpreinteBatiments + " pour " + empreinte
                    + ", " + racine.childCount + " enfant(s) pour " + enfants);
            string vide;
            using (var sha = SHA256.Create())
                vide = string.Concat(sha.ComputeHash(new byte[0]).Select(o => o.ToString("x2")));
            if (empreinte == vide)
                throw new InvalidOperationException("l'empreinte des bâtiments est celle d'un plan vide");
            Debug.Log("CAPTURE_369 " + outil.Message.Split('\n').First(l => l.StartsWith("Bâtiments : ", StringComparison.Ordinal))
                + " empreinte " + empreinte + ", " + enfants + " pièce(s)");

            // Les façades vues depuis la rue : le cap regarde à l'opposé de la façade du bâtiment du milieu.
            var coins = poses.SelectMany(b => b.Emprise).Select(c => Lot362.Monde(roads.terrain, c.X, c.Y)).ToArray();
            var centre = coins.Aggregate(Vector3.zero, (s, c) => s + c) / coins.Length;
            float cap = (float)LectureDuBatiment.Poser(poses[1]).LacetDegres + 180f;
            ville.Poser(centre, cap, INCLINAISON, DISTANCE_M);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }
    }
}
