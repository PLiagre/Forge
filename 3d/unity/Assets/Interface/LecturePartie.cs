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
        // Lot #1001 : les comptes de la maison du joueur, lus au même passage que le monde ; leur tick dit s'ils sont du même jour.
        public Lecture<ComptesDeMaison> Comptes { get; private set; }
        // Lot #1032 : le pays de la maison du joueur (ses jauges et ses points), lu au même passage ; son tick dit s'il est du même jour que le monde.
        public Lecture<PaysLu> Pays { get; private set; }
        // Lot #1045 : le reste de `/pays` (lieux, vassaux, totaux, bâtiments), lu juste après le pays ; son tick dit s'il est du même jour que le monde.
        public Lecture<TerresDuPays> Terres { get; private set; }
        public Lecture<DepartsLus> Departs { get; private set; }
        public RecuIntention Recu { get; private set; }
        public bool Occupee { get; private set; }
        readonly Func<Lecture<MondeAvecMaisonLu>> lireMonde;
        readonly Func<string, Lecture<MaisonLue>> lireMaison;
        readonly Func<Lecture<DepartsLus>> lireDeparts;
        readonly Func<long, RecuIntention> choisir;
        readonly Func<string, Lecture<ComptesDeMaison>> lireComptes;
        readonly Func<string, Lecture<PaysLu>> lirePays;
        readonly Func<string, Lecture<TerresDuPays>> lireTerres;
        public bool PeutChoisir => !Occupee && Monde != null && Monde.Presente
            && Monde.Donnees.MaisonDuJoueur == null && Departs != null && Departs.Presente && Recu?.Acceptee != true;

        public LecturePartie(Func<Lecture<MondeAvecMaisonLu>> monde, Func<string, Lecture<MaisonLue>> maison,
            Func<Lecture<DepartsLus>> departs, Func<long, RecuIntention> choisir, Func<string, Lecture<ComptesDeMaison>> comptes = null,
            Func<string, Lecture<PaysLu>> pays = null, Func<string, Lecture<TerresDuPays>> terres = null)
        {
            lireMonde = monde; lireMaison = maison; lireDeparts = departs; this.choisir = choisir; lireComptes = comptes; lirePays = pays; lireTerres = terres;
        }

        public static LecturePartie Locale(int port) => new LecturePartie(
            () => { using var c = new ClientMonde(port, TimeSpan.FromSeconds(10)); return c.LireAvecMaison(); },
            id => { using var c = new ClientMaison(port, TimeSpan.FromSeconds(10)); return c.Lire(id); },
            () => { using var c = new ClientDeparts(port, ClientDeparts.DelaiMinimal); return c.Lire(); },
            id => {
                using var c = new ClientIntention(port, TimeSpan.FromSeconds(10));
                return c.Deposer("{\"type\":\"choisir_depart\",\"seigneurie\":" + id.ToString(CultureInfo.InvariantCulture) + "}");
            },
            id => { using var c = new ClientMaison(port, TimeSpan.FromSeconds(10)); return c.LireComptes(id); },
            id => { using var c = new ClientPays(port, TimeSpan.FromSeconds(10)); return c.Lire(id); },
            id => { using var c = new ClientPays(port, TimeSpan.FromSeconds(10)); return c.LireTerres(id); });

        public async Task Actualiser()
        {
            if (Occupee) return;
            Occupee = true;
            try
            {
                var lu = await Task.Run(() => {
                    var monde = lireMonde();
                    var id = monde.Presente ? monde.Donnees.MaisonDuJoueur : null;
                    var maison = id != null ? lireMaison(id) : null;
                    var comptes = id != null && lireComptes != null ? lireComptes(id) : null;
                    var pays = id != null && lirePays != null ? lirePays(id) : null;
                    return (monde, maison, comptes, pays, terres: id != null && lireTerres != null ? lireTerres(id) : null,
                        departs: monde.Presente && id == null ? lireDeparts() : null);
                });
                Monde = lu.monde; Maison = lu.maison; Comptes = lu.comptes; Pays = lu.pays; Terres = lu.terres; Departs = lu.departs;
            }
            catch (Exception e)
            {
                Monde = Lecture<MondeAvecMaisonLu>.Absent("Lecture impossible : " + e.GetBaseException().Message);
                Maison = null; Comptes = null; Pays = null; Terres = null; Departs = null;
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
