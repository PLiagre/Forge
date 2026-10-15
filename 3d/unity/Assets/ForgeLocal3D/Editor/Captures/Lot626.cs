using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 626 : la scène Carte montre les six terres de départ. Elle s'ouvre comme au lot 549 ; le composant doit déjà
    // y être, le scénario ne l'ajoute pas. Il lit `/departs` lui-même, attend les repères posés, puis photographie la
    // carte entière. `-forge626RetirerRepere` retire un repère réel après la pose : les mêmes contrôles doivent alors
    // voir cinq objets, même si `ReperesPoses` reste à six.
    static class Lot626
    {
        const string RACINE = "Repères des terres de départ";
        const string RETIRER = "-forge626RetirerRepere";
        const double ATTENTE_S = 30;
        const int FICHES = 6;
        const int IMAGES_DE_POSE = 10;

        [ScenarioDeCapture(626, "six-terres-de-depart")]
        static IEnumerator SixTerresDeDepart(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            var carte = ouverte.Carte;
            ReperesDeDepart[] poses = carte.GetComponents<ReperesDeDepart>();
            if (poses.Length != 1)
                throw new InvalidOperationException("ReperesDeDepart : attendu 1, observé " + poses.Length);
            ReperesDeDepart reperes = poses[0];

            Task<Lecture<DepartsLus>> lecture = Lire(reperes.port);
            double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (!lecture.IsCompleted)
            {
                if (Time.realtimeSinceStartupAsDouble > fin)
                    throw new InvalidOperationException("pas de /departs en " + ATTENTE_S + " s" + Dire(reperes));
                yield return null;
            }
            if (lecture.IsFaulted)
                throw new InvalidOperationException("lecture /departs interrompue : " + lecture.Exception.GetBaseException().Message + Dire(reperes));
            IReadOnlyList<FicheDeDepart> fiches = FichesServies(lecture.Result, reperes);

            fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (reperes.LectureEnVol || reperes.TexteAffiche != null || reperes.ReperesPoses != fiches.Count || Compter(carte) != fiches.Count)
            {
                if (Time.realtimeSinceStartupAsDouble > fin)
                    throw new InvalidOperationException("pas de " + fiches.Count + " repères en " + ATTENTE_S + " s : attendu " + fiches.Count + ", observé " + Compter(carte) + " (ReperesPoses " + reperes.ReperesPoses + ")" + Dire(reperes));
                yield return null;
            }
            if (Environment.GetCommandLineArgs().Contains(RETIRER))
            {
                reperes.enabled = false;
                Object.Destroy(Actifs(carte)[0].gameObject);
                yield return null;
            }

            Lot549.Photographier(camera, carte);
            Controler(camera, carte, reperes, fiches);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Debug.Log("CAPTURE_626 " + fiches.Count + " fiches, " + Compter(carte) + " repères, ReperesPoses " + reperes.ReperesPoses + ", " + carte.CellulesPosees + " cellules posées pour " + carte.CellulesServies + " servies");
        }

        // Hors du fil de l'éditeur : `Lire` bloque, et le pas des repères doit continuer pendant l'attente.
        static Task<Lecture<DepartsLus>> Lire(int port) => Task.Run(() =>
        {
            using (var client = new ClientDeparts(port, ClientDeparts.DelaiMinimal)) return client.Lire();
        });

        static IReadOnlyList<FicheDeDepart> FichesServies(Lecture<DepartsLus> lue, ReperesDeDepart reperes)
        {
            int n = lue.Presente ? lue.Donnees.Fiches.Count : 0;
            if (!lue.Presente || n != FICHES)
                throw new InvalidOperationException("attendu " + FICHES + " fiches, observé " + n + (lue.Absence != null ? " (" + lue.Absence + ")" : "") + Dire(reperes));
            return lue.Donnees.Fiches;
        }

        static void Controler(Camera camera, CarteDessinee carte, ReperesDeDepart reperes, IReadOnlyList<FicheDeDepart> fiches)
        {
            int attendu = fiches.Count;
            List<Transform> actifs = Actifs(carte);
            if (actifs.Count != attendu || reperes.ReperesPoses != attendu)
                throw new InvalidOperationException("attendu " + attendu + " repères, observé " + actifs.Count + " (ReperesPoses " + reperes.ReperesPoses + ")" + Dire(reperes));
            var noms = new HashSet<string>();
            foreach (FicheDeDepart fiche in fiches)
            {
                string nom = "Repère " + fiche.Nom;
                if (!noms.Add(fiche.Nom))
                    throw new InvalidOperationException("fiche « " + fiche.Nom + " » en double : attendu " + attendu + " noms distincts, observé " + noms.Count);
                int comptes = 0; Transform repere = null;
                foreach (Transform t in actifs) if (t.name == nom) { comptes++; repere = t; }
                if (comptes != 1)
                    throw new InvalidOperationException("« " + nom + " » : attendu 1, observé " + comptes + Dire(reperes));
                Transform disque = repere.Find("Disque");
                MeshRenderer rendu = disque != null ? disque.GetComponent<MeshRenderer>() : null;
                int disques = rendu != null && rendu.enabled && rendu.gameObject.activeInHierarchy ? 1 : 0;
                if (disques != 1)
                    throw new InvalidOperationException("« " + nom + " » : attendu 1 disque au renderer actif, observé " + disques + Dire(reperes));
                TextMesh texte = repere.GetComponentInChildren<TextMesh>();
                if (texte == null || texte.text != fiche.Nom)
                    throw new InvalidOperationException("« " + nom + " » : attendu le nom « " + fiche.Nom + " », observé « " + (texte != null ? texte.text : "") + " »");
                Vector3 vue = camera.WorldToViewportPoint(repere.position);
                if (vue.x < 0f || vue.x > 1f || vue.y < 0f || vue.y > 1f || vue.z < camera.nearClipPlane || vue.z > camera.farClipPlane)
                    throw new InvalidOperationException("« " + fiche.Nom + " » hors champ : (" + vue.x + ", " + vue.y + ", " + vue.z + "), plans " + camera.nearClipPlane + "–" + camera.farClipPlane);
            }
            if (carte.CellulesPosees <= 0 || carte.CellulesServies <= 0 || carte.CellulesPosees != carte.CellulesServies)
                throw new InvalidOperationException(carte.CellulesPosees + " cellules posées pour " + carte.CellulesServies + " servies");
            VueDeCarte cadre = carte.Vue;
            if (cadre == null || cadre.Echelle != 1f || !camera.orthographic || Mathf.Abs(camera.orthographicSize - cadre.Demi) > 0.01f)
                throw new InvalidOperationException("la vue n'est pas la carte entière : échelle " + (cadre == null ? "absente" : cadre.Echelle.ToString()) + ", demi-hauteur caméra " + camera.orthographicSize);
        }

        static string Dire(ReperesDeDepart reperes) => reperes.TexteAffiche != null ? " : « " + reperes.TexteAffiche.Replace("\n", " | ") + " »" : "";

        static int Compter(CarteDessinee carte) => Actifs(carte).Count;

        static List<Transform> Actifs(CarteDessinee carte)
        {
            Transform racine = carte.transform.Find(RACINE);
            return racine == null ? new List<Transform>() : racine.Cast<Transform>().Where(t => t.gameObject.activeInHierarchy).ToList();
        }
    }
}
