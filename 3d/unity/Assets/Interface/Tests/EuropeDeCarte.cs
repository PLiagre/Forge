using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Forge.Pont;
using Forge.Pont.Tests;
using NUnit.Framework;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Forge.Interface.Tests
{
    // La carte de l'Europe entière posée comme le cabinet la pose, sur les réponses figées du vrai service (`EuropeDeTest`) :
    // le terrain d'un lieu par cellule, les calques, la carte de la guerre, l'atlas et les villes, lus par des lecteurs dictés. La caméra
    // regarde d'en haut, sur un écran de 1600 × 900 pixels.
    sealed class EuropeDeCarte : IDisposable
    {
        public const int ECRAN_PX = 900;
        public GameObject Racine { get; } public CarteDessinee Carte { get; } public CalquesCarte Calques { get; } public CarteDeLaGuerre Guerre { get; } public AtlasDeCarte Atlas { get; } public VillesDeCarte Villes { get; }
        readonly GameObject toile; readonly RenderTexture ecran;

        public EuropeDeCarte(Func<Lecture<AtlasLu>> atlas = null)
        {
            Racine = new GameObject("Europe témoin", typeof(CarteDessinee)); Carte = Racine.GetComponent<CarteDessinee>();
            var camera = new GameObject("Caméra témoin").AddComponent<Camera>(); camera.transform.SetParent(Racine.transform, false);
            camera.orthographic = true; camera.nearClipPlane = 1f; camera.farClipPlane = 20000f; camera.transform.SetPositionAndRotation(new Vector3(0, 5000, 0), Quaternion.Euler(90, 0, 0));
            ecran = new RenderTexture(1600, ECRAN_PX, 16); camera.targetTexture = ecran; Carte.camera = camera;
            CarteLue lue = EuropeDeTest.CarteEurope;
            Carte.Montrer(lue, new FormesLues(null, lue.Cellules.Select(c => new FormeDeCellule(c.CellId, c.Contour, new[] { new FormeDeLieu(0, c.Contour) }))));
            Assert.That(Carte.CellulesPosees, Is.EqualTo(lue.Cellules.Count), "l'Europe témoin n'est pas posée");
            toile = new GameObject("Toile témoin", typeof(Canvas));
            Calques = Racine.AddComponent<CalquesCarte>(); Calques.Initialiser(Carte, toile.transform, () => null, () => null);
            Guerre = Racine.AddComponent<CarteDeLaGuerre>(); Guerre.Installer();
            Guerre.LecteurTerres = () => Lecture<TerresDeLaCarte>.De(EuropeDeTest.TerresEurope);
            Guerre.LecteurGuerres = () => Lecture<GuerresLues>.De(new GuerresLues(EuropeDeTest.TerresEurope.Tick, EuropeDeTest.TerresEurope.Date, new GuerreLue[0], new ArmeeLue[0], new PriseLue[0], 0));
            Atlas = Racine.AddComponent<AtlasDeCarte>(); Atlas.Installer(Guerre); Atlas.LecteurAtlas = atlas ?? (() => Lecture<AtlasLu>.De(EuropeDeTest.AtlasEurope));
            Villes = Racine.AddComponent<VillesDeCarte>(); Villes.Installer(); Villes.Brancher(() => EuropeDeTest.JouablesEurope, Guerre, Atlas);
            Calques.Brancher(null, null, Guerre, Atlas, Villes); Atlas.Eviter(Calques);
            // Les terres, leur voisinage et l'atlas lus, les pays coloriés et nommés.
            double t = 0; var fin = DateTime.UtcNow.AddSeconds(90);
            while (DateTime.UtcNow < fin && (Guerre.Couleurs == null || Guerre.CotesDeFrontiere == 0 || Guerre.LectureEnVol || Atlas.LectureEnVol || (Atlas.Atlas == null && Atlas.Absence == null) || (Atlas.Atlas != null && Atlas.Ecriture == null)))
            { Guerre.Pas(t); Atlas.Pas(t); t += CarteDeLaGuerre.PERIODE_S; System.Threading.Thread.Sleep(20); }
            Assert.That(Guerre.Couleurs != null && Guerre.CotesDeFrontiere > 0, Is.True, "les pays de l'Europe ne sont pas lus : " + Guerre.AbsenceDesTerres);
            Villes.Pas();
        }

        public void Dispose() { Carte.camera.targetTexture = null; Carte.Arreter(); Object.DestroyImmediate(Racine); Object.DestroyImmediate(toile); Object.DestroyImmediate(ecran); }

        public Vector2 Ici(PointCarte point) { Vector3 v = Carte.PositionSurLaCarte(point, 0f).Value; return new Vector2(v.x, v.z); }
        // La vue centrée sur `centre` (km locaux), `demi` km de demi-hauteur ; les noms, l'atlas et les calques s'y règlent
        // trois fois : les places réservées sont celles de l'image d'avant, et l'atlas évite les capitales nommées à l'image d'avant.
        public void Voir(Vector2 centre, float demi)
        {
            Camera camera = Carte.camera; camera.transform.position = new Vector3(centre.x, 5000f, centre.y); camera.orthographicSize = demi;
            for (int i = 0; i < 3; i++) { Villes.Pas(); Guerre.SuivreLaVue(); Atlas.SuivreLaVue(); Peindre(); }
        }
        public void Peindre() => typeof(CalquesCarte).GetMethod("LateUpdate", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(Calques, null);
        // Les places des lettres de chaque nom lisible : des pays, puis de l'atlas.
        public List<Rect> LettresDesPays() { var places = new List<Rect>(); Guerre.Ecriture.Reserver(Carte.camera, places); return places; }
        public List<Rect> LettresDeLAtlas() { var places = new List<Rect>(); Atlas.Ecriture?.Reserver(Carte.camera, places); return places; }
    }
}
