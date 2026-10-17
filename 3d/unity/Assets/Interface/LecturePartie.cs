using System;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;

namespace Forge.Interface
{
    public sealed class LecturePartie
    {
        public Lecture<MondeAvecMaisonLu> Monde { get; private set; }
        public Lecture<MaisonLue> Maison { get; private set; }
        public Lecture<DepartsLus> Departs { get; private set; }
        public RecuIntention Recu { get; private set; }
        public bool Occupee { get; private set; }
        readonly Func<Lecture<MondeAvecMaisonLu>> lireMonde;
        readonly Func<string, Lecture<MaisonLue>> lireMaison;
        readonly Func<Lecture<DepartsLus>> lireDeparts;
        readonly Func<long, RecuIntention> choisir;
        public bool PeutChoisir => !Occupee && Monde != null && Monde.Presente
            && Monde.Donnees.MaisonDuJoueur == null && Departs != null && Departs.Presente && Recu?.Acceptee != true;

        public LecturePartie(Func<Lecture<MondeAvecMaisonLu>> monde, Func<string, Lecture<MaisonLue>> maison,
            Func<Lecture<DepartsLus>> departs, Func<long, RecuIntention> choisir)
        {
            lireMonde = monde; lireMaison = maison; lireDeparts = departs; this.choisir = choisir;
        }

        public static LecturePartie Locale(int port) => new LecturePartie(
            () => { using var c = new ClientMonde(port, TimeSpan.FromSeconds(10)); return c.LireAvecMaison(); },
            id => { using var c = new ClientMaison(port, TimeSpan.FromSeconds(10)); return c.Lire(id); },
            () => { using var c = new ClientDeparts(port, ClientDeparts.DelaiMinimal); return c.Lire(); },
            id => {
                using var c = new ClientIntention(port, TimeSpan.FromSeconds(10));
                return c.Deposer("{\"type\":\"choisir_depart\",\"seigneurie\":" + id.ToString(CultureInfo.InvariantCulture) + "}");
            });

        public async Task Actualiser()
        {
            if (Occupee) return;
            Occupee = true;
            try
            {
                var lu = await Task.Run(() => {
                    var monde = lireMonde();
                    var id = monde.Presente ? monde.Donnees.MaisonDuJoueur : null;
                    return (monde, maison: id != null ? lireMaison(id) : null,
                        departs: monde.Presente && id == null ? lireDeparts() : null);
                });
                Monde = lu.monde; Maison = lu.maison; Departs = lu.departs;
            }
            catch (Exception e)
            {
                Monde = Lecture<MondeAvecMaisonLu>.Absent("Lecture impossible : " + e.GetBaseException().Message);
                Maison = null; Departs = null;
            }
            finally { Occupee = false; }
        }

        public async Task Choisir(long id)
        {
            if (!PeutChoisir || !Departs.Donnees.Fiches.Any(f => f.Id == id)) return;
            Occupee = true;
            try { Recu = await Task.Run(() => choisir(id)); }
            catch (Exception e) { Recu = RecuIntention.Absente("Envoi impossible : " + e.GetBaseException().Message); }
            finally { Occupee = false; }
        }
    }
}
