using System;
using System.Collections;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Ce qu'une épreuve attend du cabinet et du service : que la lecture de la partie soit prête, qu'un
    // jour soit joué, qu'une tâche finisse, chacun dans un délai, avec la raison quand il est dépassé.
    static class AttentesDeCapture
    {
        const double ATTENTE_S = 30;

        internal static bool LecturePrete(LecturePartie p) => p != null && !p.Occupee && p.Monde != null && p.Monde.Presente && p.Monde.Donnees.MaisonDuJoueur == null
            && p.Departs != null && p.Departs.Presente && p.Departs.Donnees.Fiches.Count > 0 && p.PeutChoisir;
        internal static string Dire(LecturePartie p) => p == null ? "partie absente" : p.Occupee ? "lecture en cours" : p.Monde == null ? "monde non lu"
            : !p.Monde.Presente ? "monde absent : " + p.Monde.Absence : p.Monde.Donnees.MaisonDuJoueur != null ? "maison déjà « " + p.Monde.Donnees.MaisonDuJoueur + " »"
            : p.Departs == null || !p.Departs.Presente ? "départs absents : " + (p.Departs == null ? "non lus" : p.Departs.Absence)
            : p.Departs.Donnees.Fiches.Count == 0 ? "liste vide" : p.PeutChoisir ? "prête" : "choix impossible";        internal static Task<Lecture<MondeAvecMaisonLu>> LireMonde(int port) => Task.Run(() => { using (var c = new ClientMonde(port, TimeSpan.FromSeconds(ATTENTE_S))) return c.LireAvecMaison(); });
        internal static Task<(int statut, string corps)> PousserTick(int port) => Task.Run(() => {
            using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(ATTENTE_S) }) using (var contenu = new ByteArrayContent(new byte[0]))
            using (var reponse = http.PostAsync("http://127.0.0.1:" + port + "/tick?n=1", contenu).GetAwaiter().GetResult())
                return ((int)reponse.StatusCode, reponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()); });
        internal static IEnumerator Jusqua(Func<bool> fini, Func<string> sinon)
        { double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S; while (!fini()) { if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException(sinon() + " en " + ATTENTE_S + " s"); yield return null; } }
        internal static IEnumerator Attendre(Task tache, string cause)
        {
            for (var e = Jusqua(() => tache.IsCompleted, () => cause); e.MoveNext();) yield return null;
            if (tache.IsFaulted || tache.IsCanceled) throw new InvalidOperationException(cause + " : " + (tache.Exception == null ? tache.Status.ToString() : tache.Exception.GetBaseException().Message));
        }
    }
}
