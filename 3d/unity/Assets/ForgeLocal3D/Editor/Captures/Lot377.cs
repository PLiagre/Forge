using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 377 : le joueur pose une maison, une scierie ou un four dans la 3D. La capture tourne avec le service
    // de `sim/` sur le port 8000, à vitesse 0 : on dépose la route de plaine du jeu de gestes, un tick la met au
    // plan, l'outil rouvre la ville. Par le geste du joueur, une parcelle de 8 m × 15 m à gauche du segment 5 ;
    // puis, en mode bâtiment (touche 1), un clic sur la chaussée que l'outil refuse sans rien déposer, et un clic
    // sur la parcelle qui y dépose une maison : au tick suivant, l'outil la dessine aux piquets. Un four sur la
    // même parcelle (touche 3) passe l'outil, qui ne lit pas les bâtiments, et le monde le refuse : parcelle déjà
    // bâtie. La photo montre la rue, la parcelle au cordeau, la maison aux piquets, façade vers la rue, et le
    // panneau qui dit le refus du monde. Le plan fixe, pris avant, montre le sable vierge.
    static class Lot377
    {
        // 55° et 52 m : à 45° et 35 m la parcelle était coupée en bas, et la rue avec elle.
        const float INCLINAISON = 55f;
        const float DISTANCE_M = 52f;
        const int IMAGES_DE_POSE = 10;

        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);

        static string[] Lignes(TextMesh panneau) => panneau.text.Split('\n');

        [ScenarioDeCapture(377, "batiment-pose")]
        static IEnumerator Poser(Camera camera)
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
            var panneau = outil.view.transform.Find("Panneau des routes")?.GetComponent<TextMesh>();
            if (panneau == null)
                throw new InvalidOperationException("la caméra de l'outil n'a pas de panneau");

            int port = outil.Port;
            long cellule = outil.Cellule;
            Lot362.Deposer(port, outil.Intention(plaine));
            Lot362.Tick(port);
            var plan = Lot362.Lire(port, cellule);
            long identifiant = Lot362.Identifiant(plan, plaine);
            int n0 = plan.Parcelles.Count, b0 = plan.Batiments.Count;
            if (!outil.Ouvrir())
                throw new InvalidOperationException("l'outil n'a pas ouvert la ville : " + outil.Message);
            var terrain = roads.terrain;
            var rue = plan.Rues.First(u => u.Identifiant == identifiant);
            var vise = Lot375.Milieu(terrain, rue, 5);

            // La parcelle, par le geste : P, deux coins le long du segment 5, Entrée ; le tick la met au plan.
            outil.EntrerParcelle();
            Lot375.Cliquer(camera, ville, outil, vise, Lot375.Point(rue, 5, 1, 3), Lot375.Point(rue, 5, 9, 17));
            var tracee = outil.ValiderParcelle();
            if (tracee == null || !tracee.Presente)
                throw new InvalidOperationException("l'outil n'a pas tracé la parcelle : " + outil.Message);
            if (outil.Recu == null || !outil.Recu.Acceptee)
                throw new InvalidOperationException("la parcelle n'est pas acceptée par le monde : " + outil.Message);
            Lot362.Tick(port);
            if (!outil.Attendre())
                throw new InvalidOperationException("après le tick, l'outil n'a pas relu de plan plus récent que le dépôt de la parcelle");
            plan = Lot362.Lire(port, cellule);
            if (plan.Parcelles.Count != n0 + 1)
                throw new InvalidOperationException("le plan du tick " + plan.Tick + " compte " + plan.Parcelles.Count + " parcelle(s), il en faut " + (n0 + 1));
            var parcelle = plan.Parcelles[n0];
            long p = parcelle.Identifiant;
            if (parcelle.Contour.Count != 4)
                throw new InvalidOperationException("la parcelle " + p + " a " + parcelle.Contour.Count + " coin(s), il en faut 4");
            var c = (x: parcelle.Contour.Average(k => k.X), y: parcelle.Contour.Average(k => k.Y));

            // Échap quitte le mode bâtiment, vers le mode route.
            outil.EntrerBatiment("maison");
            outil.Annuler();
            if (outil.ModeBatiment || outil.ModeParcelle)
                throw new InvalidOperationException("Échap n'a pas ramené l'outil au mode route : " + outil.Message);

            // Le clic sur l'axe de la rue : aucune parcelle dessous, l'outil refuse et le monde n'en sait rien.
            outil.EntrerBatiment("maison");
            if (!outil.ModeBatiment || outil.ModeParcelle)
                throw new InvalidOperationException("l'outil n'est pas passé en mode bâtiment seul : " + outil.Message);
            Lot375.Cliquer(camera, ville, outil, vise, Lot375.Point(rue, 5, 4, 0));
            if (outil.Pose == null || outil.Pose.Presente || !outil.Pose.Absence.StartsWith("aucune parcelle sous le point", StringComparison.Ordinal))
                throw new InvalidOperationException("le clic sur la chaussée n'est pas refusé par l'outil faute de parcelle : " + outil.Message);
            if (outil.Recu != null)
                throw new InvalidOperationException("le clic sur la chaussée a atteint le monde : " + outil.Message);
            if (!Lignes(panneau)[0].StartsWith("Bâtiment refusé par l'outil : aucune parcelle sous le point", StringComparison.Ordinal))
                throw new InvalidOperationException("le panneau ne dit pas le refus de l'outil : " + panneau.text);

            // La maison, d'un clic au centre de la parcelle : le monde l'accepte.
            Lot375.Cliquer(camera, ville, outil, vise, c);
            if (outil.Pose == null || !outil.Pose.Presente || outil.Pose.Parcelle != p || outil.Pose.Nature != "maison")
                throw new InvalidOperationException("le clic sur la parcelle " + p + " ne forme pas une maison sur elle : " + outil.Message);
            if (outil.Recu == null || !outil.Recu.Acceptee)
                throw new InvalidOperationException("la maison n'est pas acceptée par le monde : " + outil.Message);
            if (!Lignes(panneau).Any(l => l.StartsWith("Bâtiment déposé au monde : maison sur la parcelle " + N(p), StringComparison.Ordinal)))
                throw new InvalidOperationException("le panneau ne dit pas le dépôt de la maison : " + panneau.text);
            if (!outil.ModeBatiment)
                throw new InvalidOperationException("l'outil a quitté le mode bâtiment après le dépôt");

            // Le tick : la maison entre au plan en chantier, l'outil la dessine aux piquets.
            Lot362.Tick(port);
            if (!outil.Attendre())
                throw new InvalidOperationException("après le tick, l'outil n'a pas relu de plan plus récent que le dépôt de la maison");
            plan = Lot362.Lire(port, cellule);
            if (plan.Batiments.Count != b0 + 1)
                throw new InvalidOperationException("le plan du tick " + plan.Tick + " compte " + plan.Batiments.Count + " bâtiment(s), il en faut " + (b0 + 1));
            var b = plan.Batiments[plan.Batiments.Count - 1];
            if (b.Parcelle != p || b.Nature != "maison" || !b.EnChantier)
                throw new InvalidOperationException("le bâtiment " + b.Identifiant + " est " + b.Nature + " sur la parcelle " + b.Parcelle
                    + (b.EnChantier ? " en chantier" : " achevé") + ", il faut une maison en chantier sur la parcelle " + p);
            if (LectureDuBatiment.Etape(b) != EtapeDuBatiment.Piquets)
                throw new InvalidOperationException("le bâtiment " + b.Identifiant + " est à l'étape " + LectureDuBatiment.Etape(b) + " ("
                    + b.TravailFourni + "/" + b.TravailRequis + "), il faut les piquets");
            var dessin = outil.Batiments.Where(e => e.identifiant == b.Identifiant).ToArray();
            if (dessin.Length != 1 || dessin[0].etat != "piquets")
                throw new InvalidOperationException("le bâtiment " + b.Identifiant + " n'est pas dessiné aux piquets : "
                    + string.Join(", ", outil.Batiments.Select(e => e.identifiant + " " + e.etat)) + " (" + outil.Message + ")");
            if (outil.RacineBatiments == null || outil.RacineBatiments.Find("Bâtiment " + N(b.Identifiant)) == null)
                throw new InvalidOperationException("pas d'enfant « Bâtiment " + b.Identifiant + " » sous la racine des bâtiments");
            if (!Lignes(panneau).Any(l => l.StartsWith("Bâtiments : ", StringComparison.Ordinal)))
                throw new InvalidOperationException("le panneau ne compte pas les bâtiments : " + panneau.text);

            // Un four sur la même parcelle : l'outil, qui ne lit pas les bâtiments, le forme ; le monde le refuse.
            outil.EntrerBatiment("four");
            Lot375.Cliquer(camera, ville, outil, vise, c);
            if (outil.Pose == null || !outil.Pose.Presente)
                throw new InvalidOperationException("l'outil a refusé lui-même le four, le refus doit venir du monde : " + outil.Message);
            if (outil.Recu == null || !outil.Recu.Presente || outil.Recu.Acceptee)
                throw new InvalidOperationException("le four n'a pas de reçu de refus du monde : " + outil.Message);
            string attendu = "parcelle déjà bâtie : " + N(p);
            if (outil.Recu.Erreur != attendu)
                throw new InvalidOperationException("le monde refuse le four pour « " + outil.Recu.Erreur + " », il faut « " + attendu + " »");
            if (Lignes(panneau)[0] != "Le monde refuse le bâtiment : " + attendu)
                throw new InvalidOperationException("le panneau ne dit pas le refus du monde : " + panneau.text);
            Lot362.Tick(port);
            plan = Lot362.Lire(port, cellule);
            var surP = plan.Batiments.Where(x => x.Parcelle == p).ToArray();
            if (plan.Batiments.Count != b0 + 1 || surP.Length != 1 || surP[0].Identifiant != b.Identifiant || surP[0].Nature != "maison")
                throw new InvalidOperationException("après le refus, le plan du tick " + plan.Tick + " compte " + plan.Batiments.Count
                    + " bâtiment(s) (il en faut " + (b0 + 1) + "), dont sur la parcelle " + p + " : "
                    + string.Join(", ", surP.Select(x => x.Identifiant + " " + x.Nature)));

            Debug.Log("CAPTURE_377 " + panneau.text.Replace("\n", " | "));

            // La façade vue depuis la rue : le cap regarde à l'opposé de la façade de la maison.
            var centre = Lot362.Monde(terrain, c.x, c.y);
            float cap = (float)LectureDuBatiment.Poser(b).LacetDegres + 180f;
            ville.Poser(centre, cap, INCLINAISON, DISTANCE_M);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }
    }
}
