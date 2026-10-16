using System;
using System.Collections;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Lot 613 : un clic sur le repère d'une terre dépose son choix au service, et l'écran dit le reçu. La carte s'ouvre comme
    // au lot 549, survol et parcours en automatique ; une fois les six repères posés, le scénario lit `/departs` lui-même,
    // puis clique par `SurvolDeCarte`, comme le joueur, sur la Morée (acceptée au tick publié) puis sur le Zab (refusé : le
    // départ est déjà choisi). `-forge613SansPremierChoix` saute le clic sur la Morée : le Zab est accepté, la capture rougit.
    static class Lot613
    {
        const string RACINE = "Repères des terres de départ", MOREE = "Despotat de Morée", SIEGE_DU_ZAB = "Biskra";
        const string REFUS = "départ déjà choisi : seigneurie-3", SANS_PREMIER_CHOIX = "-forge613SansPremierChoix";
        const double ATTENTE_S = 30;
        const int FICHES = 6, CONFLIT = 409, IMAGES_DE_POSE = 10;

        [ScenarioDeCapture(613, "second-choix-refuse")]
        static IEnumerator SecondChoixRefuse(Camera camera)
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
            for (var e = Attendre(() => !reperes.LectureEnVol && Actifs(carte) == FICHES, () => "attendu " + FICHES + " repères actifs, observé " + Actifs(carte)
                + (reperes.LectureEnVol ? ", lecture en vol" : "") + " : « " + reperes.TexteAffiche + " »"); e.MoveNext();) yield return null;

            int port = reperes.port;
            var lecture = Task.Run(() => { using (var d = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) return d.Lire(); });
            for (var e = Attendre(() => lecture.IsCompleted, () => "pas de /departs"); e.MoveNext();) yield return null;
            if (lecture.IsFaulted) throw new InvalidOperationException("lecture interrompue : " + lecture.Exception.GetBaseException().Message);
            var departs = lecture.Result;
            if (!departs.Presente) throw new InvalidOperationException("attendu /departs servi, observé « " + departs.Absence + " »");
            long tick = departs.Donnees.Tick; // le tick publié : le pilote ne passe pas `-forgeTicks`, rien n'est figé
            FicheDeDepart moree = departs.Donnees.Fiches.FirstOrDefault(f => f.Nom == MOREE) ?? throw new InvalidOperationException("/departs ne sert pas « " + MOREE + " »");
            FicheDeDepart zab = departs.Donnees.Fiches.FirstOrDefault(f => f.Siege.Nom == SIEGE_DU_ZAB) ?? throw new InvalidOperationException("/departs ne sert pas de terre au siège " + SIEGE_DU_ZAB);

            string premier = "sauté";
            if (!Environment.GetCommandLineArgs().Contains(SANS_PREMIER_CHOIX))
            {
                for (var e = Cliquer(carte, survol, reperes, moree); e.MoveNext();) yield return null;
                RecuIntention recu = reperes.RecuDuChoix; premier = reperes.ChoixAffiche;
                if (!recu.Acceptee || recu.AppliqueeAuTick != tick) throw new InvalidOperationException("choix de la Morée : attendu accepté au tick " + tick + ", observé " + Dire(recu));
                if (premier != ReperesDeDepart.DireLeChoix(moree, recu)) throw new InvalidOperationException("choix affiché : attendu « " + ReperesDeDepart.DireLeChoix(moree, recu) + " », observé « " + premier + " »");
            }

            for (var e = Cliquer(carte, survol, reperes, zab); e.MoveNext();) yield return null;
            RecuIntention refus = reperes.RecuDuChoix; string attendu = ReperesDeDepart.DireLeChoix(zab, refus), vu = reperes.ChoixAffiche;
            if (refus.Statut != CONFLIT || refus.Erreur != REFUS) throw new InvalidOperationException("refus attendu pour " + zab.Nom + " : statut " + CONFLIT + " « " + REFUS + " », observé " + Dire(refus));
            if (vu != attendu) throw new InvalidOperationException("refus affiché : attendu « " + attendu + " », observé « " + vu + " »");
            if (reperes.Survolee?.Id != zab.Id) throw new InvalidOperationException("terre survolée : attendu « " + zab.Nom + " », observé « " + reperes.Survolee?.Nom + " »");
            // La fiche de cellule dit ses habitants une fois le monde lu : la photo la montre entière.
            for (var e = Attendre(() => cellule.MondeLu != null, () => "pas de monde lu : « " + cellule.TexteAffiche + " »"); e.MoveNext();) yield return null;

            Lot549.Photographier(camera, carte);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (reperes.ChoixAffiche != attendu) throw new InvalidOperationException("le choix affiché a changé pendant la pose : « " + reperes.ChoixAffiche + " »");
            Debug.Log("CAPTURE_613 premier choix : " + premier.Replace("\n", " | ") + " ; second choix : " + vu.Replace("\n", " | "));
        }

        // Le clic du joueur, par le survol de la carte, sur le disque de la terre ; puis l'attente du reçu de son dépôt.
        static IEnumerator Cliquer(CarteDessinee carte, SurvolDeCarte survol, ReperesDeDepart reperes, FicheDeDepart terre)
        {
            Transform repere = carte.transform.Find(RACINE + "/Repère " + terre.Nom) ?? throw new InvalidOperationException("pas de « Repère " + terre.Nom + " » sous « " + RACINE + " »");
            Vector2 ecran = carte.camera.WorldToScreenPoint(repere.position);
            survol.Survoler(ecran); survol.Cliquer(ecran);
            if (!reperes.ChoixEnVol || reperes.TerreDuChoix?.Id != terre.Id) throw new InvalidOperationException("clic sur « " + terre.Nom + " » : attendu un dépôt en vol, observé "
                + (reperes.ChoixEnVol ? "un dépôt pour « " + reperes.TerreDuChoix?.Nom + " »" : "aucun dépôt") + ", terre survolée « " + reperes.Survolee?.Nom + " »");
            for (var e = Attendre(() => !reperes.ChoixEnVol, () => "pas de reçu pour « " + terre.Nom + " »"); e.MoveNext();) yield return null;
        }

        static IEnumerator Attendre(Func<bool> fini, Func<string> sinon)
        {
            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (!fini()) { if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException(sinon() + " en " + ATTENTE_S + " s"); yield return null; }
        }

        static string Dire(RecuIntention recu) =>
            recu.Acceptee ? "accepté au tick " + recu.AppliqueeAuTick : recu.Presente ? "statut " + recu.Statut + " « " + recu.Erreur + " »" : "absent : " + recu.Absence;

        static int Actifs(CarteDessinee carte) { Transform racine = carte.transform.Find(RACINE); return racine == null ? 0 : racine.Cast<Transform>().Count(t => t.gameObject.activeInHierarchy); }
    }
}
