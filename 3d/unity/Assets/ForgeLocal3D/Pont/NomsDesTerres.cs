using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;

namespace Forge.Pont
{
    // Le nom servi de chaque lieu, lu une fois par terre au service local, jamais fabriqué ici.
    // Une seule lecture à la fois, hors du fil principal ; un lieu lu se garde pour la session,
    // un échec garde sa cause et ne se retente qu'après ATTENTE_APRES_ECHEC_S. Appelé seulement depuis le fil principal.
    public sealed class NomsDesTerres
    {
        public const double ATTENTE_APRES_ECHEC_S = 2;
        private readonly Func<long, LectureLieu> lire;
        private readonly Dictionary<long, Lieu> lus = new Dictionary<long, Lieu>();
        private readonly Dictionary<long, (string Cause, double Reprise)> echecs = new Dictionary<long, (string Cause, double Reprise)>();
        private Task<LectureLieu> enVol;
        private long celluleEnVol;

        public NomsDesTerres(Func<long, LectureLieu> lire) { this.lire = lire ?? throw new ArgumentNullException(nameof(lire)); }

        public static NomsDesTerres Local(int port)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port), port, "port hors de 1..65535");
            return new NomsDesTerres(cellId => { using (var client = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return client.Lire(cellId); });
        }

        public bool LectureEnVol => enVol != null && !enVol.IsCompleted;

        public string Nom(long cellId, long rang, double maintenant)
        {
            Relever(maintenant);
            if (lus.TryGetValue(cellId, out Lieu lieu)) return Place(lieu, rang)?.Nom;
            if (enVol == null && (!echecs.TryGetValue(cellId, out var echec) || maintenant >= echec.Reprise))
            {
                celluleEnVol = cellId;
                enVol = Task.Run(() =>
                {
                    try { return lire(cellId) ?? LectureLieu.Absent("aucune lecture rendue"); }
                    catch (Exception erreur) { return LectureLieu.Absent(erreur.GetBaseException().Message); }
                });
            }
            return null;
        }

        public string Bourg(long cellId, double maintenant) => Nom(cellId, 0, maintenant);

        public string Raison(long cellId, long rang)
        {
            if (!lus.TryGetValue(cellId, out Lieu lieu)) return echecs.TryGetValue(cellId, out var echec) ? echec.Cause : "nom en cours de lecture";
            if (lieu.Lieux == null) return lieu.AbsenceDesLieux ?? "lieux non fournis";
            LieuPlace place = Place(lieu, rang);
            return place == null ? "aucun lieu de ce rang dans la terre" : place.AbsenceDuNom;
        }

        // Comme `Lieu.Bourg` : le rang cherché, où qu'il soit dans la liste.
        private static LieuPlace Place(Lieu lieu, long rang) => lieu.Lieux?.FirstOrDefault(place => place.Rang == rang);

        // Une lecture finie devient un lieu gardé ou un échec daté de l'appel qui le relève ; une exception devient une absence.
        private void Relever(double maintenant)
        {
            if (enVol == null || !enVol.IsCompleted) return;
            string prefixe = "lieu " + celluleEnVol.ToString(CultureInfo.InvariantCulture) + " : ";
            LectureLieu lecture = enVol.Status != TaskStatus.RanToCompletion
                ? LectureLieu.Absent(prefixe + (enVol.Exception?.GetBaseException().Message ?? "lecture annulée"))
                : enVol.Result ?? LectureLieu.Absent(prefixe + "aucune lecture rendue");
            enVol = null;
            if (lecture.Presente) { lus[celluleEnVol] = lecture.Lieu; echecs.Remove(celluleEnVol); }
            else echecs[celluleEnVol] = (lecture.Absence, maintenant + ATTENTE_APRES_ECHEC_S);
        }
    }
}
