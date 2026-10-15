using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Lot 624 : la souris sur le repère d'une terre ouvre sa fiche en bas à droite. La carte s'ouvre comme au lot 549, son
    // survol et son parcours en automatique ; une fois les six repères posés, le scénario lit lui-même `/departs` et la
    // maison de la Morée, puis pose la souris sur le disque de la Morée par `SurvolDeCarte`, comme le ferait le joueur. La
    // fiche doit dire ce que le service sert, et la fiche de cellule voir la même place. `-forge624HorsRepere` vise un
    // diamètre plus à l'est : aucune terre n'est survolée, la capture doit rougir.
    static class Lot624
    {
        const string RACINE = "Repères des terres de départ";
        const string MOREE = "Despotat de Morée";
        const string MAISON = "seigneurie-3";
        const string HORS_REPERE = "-forge624HorsRepere";
        const double ATTENTE_S = 30;
        const int FICHES = 6;
        // Le tick où la capture a poussé le service : `-forgeTicks` (3 dans SC5), sinon le défaut de `ForgeCapture`, car le
        // pilote du PC ne passe pas l'argument. Un 3 figé rougissait la validation du PC (tick servi 30).
        const string TICKS = "-forgeTicks";
        const long TICKS_PAR_DEFAUT = 30;
        const int IMAGES_DE_POSE = 10;

        [ScenarioDeCapture(624, "fiche-de-la-moree")]
        static IEnumerator FicheDeLaMoree(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            var carte = ouverte.Carte;
            var survol = carte.GetComponent<SurvolDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas de survol");
            var cellule = carte.GetComponent<FicheDeCellule>() ?? throw new InvalidOperationException("la carte n'a pas de fiche de cellule");
            (carte.GetComponent<ParcoursDeCarte>() ?? throw new InvalidOperationException("la carte n'a pas de parcours")).automatique = true;
            survol.automatique = true;
            ReperesDeDepart[] poses = carte.GetComponents<ReperesDeDepart>();
            if (poses.Length != 1) throw new InvalidOperationException("ReperesDeDepart : attendu 1, observé " + poses.Length);
            ReperesDeDepart reperes = poses[0];

            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (reperes.LectureEnVol || Actifs(carte) != FICHES)
            {
                if (Time.realtimeSinceStartupAsDouble > fin)
                    throw new InvalidOperationException("attendu " + FICHES + " repères actifs en " + ATTENTE_S + " s, observé " + Actifs(carte) + (reperes.LectureEnVol ? ", lecture en vol" : "") + " : « " + reperes.TexteAffiche + " »");
                yield return null;
            }

            int port = reperes.port;
            var lecture = Task.Run(() =>
            {
                using (var d = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) using (var m = new ClientMaison(port, ClientDeparts.DelaiMinimal))
                    return (departs: d.Lire(), maison: m.Lire(MAISON));
            });
            fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (!lecture.IsCompleted)
            {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException("pas de /departs ni de /maison?id=" + MAISON + " en " + ATTENTE_S + " s");
                yield return null;
            }
            if (lecture.IsFaulted) throw new InvalidOperationException("lecture interrompue : " + lecture.Exception.GetBaseException().Message);
            var (departs, maison) = lecture.Result;
            if (!departs.Presente || !maison.Presente) throw new InvalidOperationException("attendu /departs et /maison servis, observé « " + departs.Absence + " » et « " + maison.Absence + " »");
            string[] args = Environment.GetCommandLineArgs(); int place = Array.IndexOf(args, TICKS);
            long tick = place >= 0 && place + 1 < args.Length ? long.Parse(args[place + 1], CultureInfo.InvariantCulture) : TICKS_PAR_DEFAUT;
            if (departs.Donnees.Tick != tick) throw new InvalidOperationException("tick lu : attendu " + tick + ", observé " + departs.Donnees.Tick);
            FicheDeDepart moree = departs.Donnees.Fiches.FirstOrDefault(f => f.Nom == MOREE) ?? throw new InvalidOperationException("/departs ne sert pas « " + MOREE + " »");

            Transform repere = carte.transform.Find(RACINE + "/Repère " + MOREE) ?? throw new InvalidOperationException("pas de « Repère " + MOREE + " » sous « " + RACINE + " »");
            Vector3 vise = repere.position;
            if (Environment.GetCommandLineArgs().Contains(HORS_REPERE)) vise += carte.transform.TransformVector(Vector3.right * ReperesDeDepart.DIAMETRE_REPERE_KM);
            survol.Survoler(carte.camera.WorldToScreenPoint(vise));

            if (reperes.Survolee == null) throw new InvalidOperationException("aucune terre survolée : attendu « " + MOREE + " »");
            if (reperes.Survolee.Nom != MOREE) throw new InvalidOperationException("terre survolée : attendu « " + MOREE + " », observé « " + reperes.Survolee.Nom + " »");
            string attendue = ReperesDeDepart.Decrire(moree, departs.Donnees.Tick, maison.Donnees), vue = reperes.FicheAffichee;
            if (vue != attendue || new[] { "Mistra", "Paléologue", "Byzance" }.Any(m => !attendue.Contains(m)))
                throw new InvalidOperationException("fiche de la terre : attendu « " + attendue + " », observé « " + vue + " »");
            if (cellule.Survolee == null || cellule.Survolee.CellId != moree.CellId)
                throw new InvalidOperationException("fiche de cellule : attendu la cellule " + moree.CellId + ", observé " + (cellule.Survolee == null ? "aucune" : cellule.Survolee.CellId.ToString()));

            // La fiche de cellule dit ses habitants une fois le monde lu : la photo la montre entière.
            fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (cellule.MondeLu == null)
            {
                if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException("pas de monde lu en " + ATTENTE_S + " s : « " + cellule.TexteAffiche + " »");
                yield return null;
            }

            Lot549.Photographier(camera, carte);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (reperes.FicheAffichee != attendue) throw new InvalidOperationException("la fiche de la terre a changé pendant la pose : « " + reperes.FicheAffichee + " »");
            Debug.Log("CAPTURE_624 " + reperes.FicheAffichee.Replace("\n", " | ") + " ; cellule " + cellule.Survolee.CellId);
        }

        static int Actifs(CarteDessinee carte)
        {
            Transform racine = carte.transform.Find(RACINE);
            return racine == null ? 0 : racine.Cast<Transform>().Count(t => t.gameObject.activeInHierarchy);
        }
    }
}
