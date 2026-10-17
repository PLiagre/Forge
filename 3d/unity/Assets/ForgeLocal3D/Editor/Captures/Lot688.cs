using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 688 : la ville s'ouvre sur le siège du joueur. La capture tourne dans l'éditeur, donc sur le ksar de 1175 ; le
    // scénario lit `/departs`, choisit le Zab, joue un tick, puis rejoue le lancement du jeu bâti sans argument :
    // `outil.Lancer(["Forge.exe"], false, panneau)`. La ville doit s'ouvrir sur la cellule de Biskra, et le panneau du lieu
    // la lire, sans jamais repasser par 1175 ni déplacer la caméra. La photo est la vue d'ensemble du joueur (touche F).
    // Contre-épreuves : -forge688SansChoix omet le choix (la scène passe à la carte) ; -forge688SansPanneau ne passe pas le
    // panneau à Lancer (il reste à 1175) ; -forge688CelluleFautive lance avec `-forgeCell abc` (une absence, aucun plan).
    static class Lot688
    {
        const string SIEGE = "Biskra", KSAR = "Cellule 1175";
        const string SANS_CHOIX = "-forge688SansChoix", SANS_PANNEAU = "-forge688SansPanneau", CELLULE_FAUTIVE = "-forge688CelluleFautive";
        const double ATTENTE_S = 30, ATTENTE_PANNEAU_S = 15;
        const float ECART_POSE = 1e-3f;
        const int IMAGES_DE_CARTE = 10, IMAGES_DE_POSE = 10;

        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);
        static bool Drapeau(string nom) => Environment.GetCommandLineArgs().Contains(nom);
        static string Ligne(string texte) => texte == null ? "(aucun texte)" : texte.Split('\n')[0];

        // Le panneau du lieu ne doit jamais redire le ksar après Lancer : vérifié à chaque image.
        static void SansKsar(PanneauLieu panneau, string etape)
        {
            string texte = panneau.TexteAffiche;
            if (texte != null && texte.Contains(KSAR))
                throw new InvalidOperationException(etape + " : le panneau du lieu dit encore « " + texte.Replace("\n", " | ") + " » après Lancer");
        }

        static string Pose(DesertCityCamera v) => "vise " + v.Vise.ToString("F3") + ", cap " + v.Cap.ToString("0.###", CultureInfo.InvariantCulture)
            + ", inclinaison " + v.Inclinaison.ToString("0.###", CultureInfo.InvariantCulture) + ", distance " + v.Distance.ToString("0.###", CultureInfo.InvariantCulture);

        [ScenarioDeCapture(688, "biskra-au-lancement")]
        static IEnumerator BiskraAuLancement(Camera camera)
        {
            // 1. L'outil, la caméra de la ville (celle de la photo) et le panneau du lieu, encore sur le ksar.
            var outil = Object.FindFirstObjectByType<DesertRoadTool>() ?? throw new InvalidOperationException("étape 1 : la scène n'a pas de DesertRoadTool");
            var ville = Object.FindFirstObjectByType<DesertCityCamera>() ?? throw new InvalidOperationException("étape 1 : la scène n'a pas de DesertCityCamera");
            var panneau = Object.FindFirstObjectByType<PanneauLieu>() ?? throw new InvalidOperationException("étape 1 : la scène n'a pas de PanneauLieu");
            if (ville.GetComponent<Camera>() != camera)
                throw new InvalidOperationException("étape 1 : la DesertCityCamera n'est pas sur la caméra de la photo « " + camera.name + " »");
            outil.automatique = true; ville.automatique = true;
            string avant = panneau.TexteAffiche ?? "";
            if (!avant.StartsWith(KSAR + " · tick ", StringComparison.Ordinal))
                throw new InvalidOperationException("étape 1 : sans -forgeCell, le panneau du lieu devait lire le ksar, il dit « " + avant.Replace("\n", " | ") + " »");

            // 2. La pose de la caméra, que l'ouverture ne doit pas toucher.
            Vector3 vise = ville.Vise; float cap = ville.Cap, inclinaison = ville.Inclinaison, distance = ville.Distance;
            string poseAvant = Pose(ville);

            // 3. L'unique terre au siège de Biskra, lue dans `/departs` hors du fil de l'éditeur.
            int port = outil.Port;
            var lecture = Task.Run(() => { using (var d = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) return d.Lire(); });
            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (!lecture.IsCompleted)
            {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException("étape 3 : pas de /departs en " + ATTENTE_S + " s");
                yield return null;
            }
            if (lecture.IsFaulted) throw new InvalidOperationException("étape 3 : lecture interrompue : " + lecture.Exception.GetBaseException().Message);
            if (!lecture.Result.Presente) throw new InvalidOperationException("étape 3 : /departs absent : " + lecture.Result.Absence);
            long tick = lecture.Result.Donnees.Tick;
            var zab = lecture.Result.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (zab.Length != 1) throw new InvalidOperationException("étape 3 : /departs compte " + zab.Length + " fiche(s) au siège " + SIEGE + ", il en faut une");
            long seigneurie = zab[0].Id, cellule = zab[0].CellId;
            if (!avant.StartsWith(KSAR + " · tick " + N(tick) + "\n", StringComparison.Ordinal))
                throw new InvalidOperationException("étape 1 : le panneau du ksar dit « " + Ligne(avant) + " », attendu au tick " + N(tick) + " servi");

            // 4. Le choix du Zab, appliqué par un tick ; sans choix, le tick est joué quand même.
            if (!Drapeau(SANS_CHOIX)) Lot362.Deposer(port, "{\"type\":\"choisir_depart\",\"seigneurie\":" + N(seigneurie) + "}");
            Lot362.Tick(port);

            // 5. Le lancement du jeu bâti, sans argument (ou avec une cellule fautive).
            string[] arguments = Drapeau(CELLULE_FAUTIVE) ? new[] { "Forge.exe", PanneauLieu.ARGUMENT_CELLULE, "abc" } : new[] { "Forge.exe" };
            var decision = outil.Lancer(arguments, false, Drapeau(SANS_PANNEAU) ? null : panneau);
            string dite = decision.Presente ? decision.Donnees.Mode + (decision.Donnees.Cellule is long c ? " " + N(c) : "") + (decision.Donnees.Scene != null ? " " + decision.Donnees.Scene : "")
                : "absence « " + decision.Absence + " »";

            if (decision.Presente && decision.Donnees.Mode == ModeDOuverture.Carte)
            {
                // La scène change à l'image suivante : l'outil et le panneau disparaissent avec le ksar.
                for (int i = 0; i < IMAGES_DE_CARTE && SceneManager.GetActiveScene().name != OuvertureDeLaCarte.SCENE; i++) yield return null;
                string active = SceneManager.GetActiveScene().name;
                Debug.Log("CAPTURE_688 " + SIEGE + ", seigneurie " + N(seigneurie) + ", décision " + dite + ", scène active " + active);
                throw new InvalidOperationException((Drapeau(SANS_CHOIX) ? "sans choix, la ville passe à la carte" : "étape 5 : le Zab choisi, la ville passe pourtant à la carte")
                    + " : scène active " + active);
            }

            if (Drapeau(CELLULE_FAUTIVE))
            {
                PanneauLieu.LireCellule(arguments, PanneauLieu.CELLULE_PAR_DEFAUT, out string erreur);
                if (erreur == null) throw new InvalidOperationException("SC4 : les arguments " + string.Join(" ", arguments) + " ne donnent aucune erreur de cellule");
                if (decision.Presente || decision.Absence != erreur)
                    throw new InvalidOperationException("SC4 : Lancer rend " + dite + ", attendu l'absence « " + erreur + " »");
                bool ouverte = outil.Ouvrir();
                var manques = new[] {
                    (ouverte, "Ouvrir() a ouvert un plan"), (outil.Message != erreur, "le panneau des routes dit « " + outil.Message + " »"),
                    (outil.TickOuverture != -1, "un plan du tick " + N(outil.TickOuverture) + " est ouvert"), (panneau.enabled, "le panneau du lieu est resté allumé")
                }.Where(x => x.Item1).Select(x => x.Item2).ToArray();
                if (manques.Length > 0) throw new InvalidOperationException("SC4 : " + string.Join(" | ", manques));
                throw new InvalidOperationException("absence : " + erreur + " ; aucun plan ouvert ; panneau du lieu éteint");
            }

            if (!decision.Presente || decision.Donnees.Mode != ModeDOuverture.Ville || decision.Donnees.Cellule != cellule || outil.Cellule != cellule)
                throw new InvalidOperationException("étape 5 : Lancer rend " + dite + " et l'outil est sur la cellule " + N(outil.Cellule) + ", attendu Ville " + N(cellule));

            // 6. La ville de Biskra, dessinée d'après le plan du tick qui a appliqué le choix.
            if (!outil.Ouvrir() || outil.TickOuverture != tick + 1)
                throw new InvalidOperationException("étape 6 : Ouvrir() n'a pas ouvert le plan du tick " + N(tick + 1) + " (tick " + N(outil.TickOuverture) + ") : " + outil.Message);

            // 7. Le panneau du lieu lit Biskra au tick suivant, sans jamais redire le ksar.
            string attendu = "Cellule " + N(cellule) + " · tick " + N(tick + 1) + "\n";
            fin = Time.realtimeSinceStartupAsDouble + ATTENTE_PANNEAU_S;
            while (!(panneau.TexteAffiche ?? "").StartsWith(attendu, StringComparison.Ordinal))
            {
                SansKsar(panneau, "étape 7");
                if (Time.realtimeSinceStartupAsDouble > fin)
                    throw new InvalidOperationException("étape 7 : en " + ATTENTE_PANNEAU_S + " s, le panneau du lieu dit « " + (panneau.TexteAffiche ?? "").Replace("\n", " | ") + " », attendu « " + attendu.Trim() + " … »");
                yield return null;
            }
            SansKsar(panneau, "étape 7");

            // 8. L'ouverture n'a pas déplacé la caméra.
            if (Vector3.Distance(ville.Vise, vise) > ECART_POSE || Mathf.Abs(Mathf.DeltaAngle(ville.Cap, cap)) > ECART_POSE
                || Mathf.Abs(ville.Inclinaison - inclinaison) > ECART_POSE || Mathf.Abs(ville.Distance - distance) > ECART_POSE)
                throw new InvalidOperationException("étape 8 : la caméra a bougé : " + poseAvant + " avant, " + Pose(ville) + " après");

            // 9. Le relevé.
            Debug.Log("CAPTURE_688 " + SIEGE + ", seigneurie " + N(seigneurie) + ", cellule " + N(outil.Cellule) + ", tick " + N(tick)
                + ", décision " + dite + ", panneau « " + Ligne(panneau.TexteAffiche) + " »");

            // La photo : la touche F du joueur, même point visé et même cap, à 40° et au plus loin.
            ville.VueEnsemble();
            if (Mathf.Abs(ville.Vise.x - vise.x) > ECART_POSE || Mathf.Abs(ville.Vise.z - vise.z) > ECART_POSE || Mathf.Abs(Mathf.DeltaAngle(ville.Cap, cap)) > ECART_POSE)
                throw new InvalidOperationException("vue d'ensemble : " + Pose(ville) + ", attendue au point visé et au cap de " + poseAvant);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
            {
                yield return null;
                SansKsar(panneau, "pose de la photo");
            }
            Debug.Log("CAPTURE_688 photo : " + Pose(ville) + " · panneau « " + (panneau.TexteAffiche ?? "").Replace("\n", " | ") + " » · foyers « "
                + (panneau.TexteFoyers ?? "").Replace("\n", " | ") + " »");
        }
    }
}
