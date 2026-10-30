using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Forge.Pont;
using UnityEngine;
using Object=UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 907 : tours, pans et porte de l'enceinte servie, à l'étape du chantier. Une pièce absente ou hors du terrain se déclare.
    public sealed class DesertEnceinte
    {
        public Transform Racine{get;}
        public KitDesBatiments Kit{get;set;}
        public int Posees{get;private set;}
        public List<string> Refus{get;}=new();
        public string Empreinte{get;private set;}=Hacher("");
        readonly Terrain terrain;

        public DesertEnceinte(Transform parent,Terrain terrain,KitDesBatiments kit)
        {
            if(!kit)throw new InvalidOperationException("Pas de kit des bâtiments (Resources/KitDesBatiments) : l'enceinte n'est pas dessinée.");
            Kit=kit;this.terrain=terrain;
            var go=new GameObject("Enceinte du plan");go.transform.SetParent(parent,false);Racine=go.transform;
        }

        public string Dessiner(EnceinteDuPlan e,IReadOnlyList<PorteDuPlan> portes)
        {
            for(int i=Racine.childCount-1;i>=0;i--)Object.DestroyImmediate(Racine.GetChild(i).gameObject);
            Posees=0;Refus.Clear();
            if(e==null){Empreinte=Hacher("");return "";}
            var d=PansDeLEnceinte.Decouper(e,portes);
            if(!d.Presente){Empreinte=Hacher("");return "Enceinte non dessinée : "+d.Absence;}
            var etape=PansDeLEnceinte.Etape(e);var desc=new StringBuilder();var inv=CultureInfo.InvariantCulture;
            float limite=terrain.terrainData.size.x/2-1;int tours=0,pans=0,nbPortes=0;
            for(int i=0;i<d.Pieces.Count;i++)
            {
                var p=d.Pieces[i];string nom=p.Nature==NatureDePiece.Tour?"tour":p.Nature==NatureDePiece.Porte?"porte":"courtine";
                if(desc.Length>0)desc.Append('\n');
                string cause=null;float sx=1f;Transform pose=null;string prefab=null;
                if(Math.Abs(p.CentreX)>limite||Math.Abs(p.CentreY)>limite)cause="hors du terrain.";
                else
                {
                    var piece=Kit.Piece(nom,etape);
                    if(!piece.Presente)cause=piece.Absence;
                    else
                    {
                        sx=p.Nature==NatureDePiece.Pan?(float)(p.LongueurM/PansDeLEnceinte.LongueurPanM):1f;
                        var centre=new Vector3((float)-p.CentreX,0,(float)-p.CentreY);centre.y=terrain.SampleHeight(centre)+terrain.transform.position.y;
                        var go=Object.Instantiate(piece.Prefab,Racine);go.name="Enceinte "+nom+" "+p.Cote.ToString(inv)+"-"+p.Indice.ToString(inv);
                        go.transform.SetPositionAndRotation(centre,Quaternion.Euler(0,(float)p.LacetDegres,0));go.transform.localScale=new Vector3(sx,1f,1f);
                        pose=go.transform;prefab=piece.Prefab.name;Posees++;
                        if(p.Nature==NatureDePiece.Tour)tours++;else if(p.Nature==NatureDePiece.Porte)nbPortes++;else pans++;
                    }
                }
                if(cause!=null){Refus.Add("Pièce "+i.ToString(inv)+" de l'enceinte non posée : "+cause);desc.Append(i.ToString(inv)).Append(" refusee");continue;}
                var v=pose.position;desc.Append(i.ToString(inv)).Append(' ').Append(nom).Append(' ').Append(p.Cote.ToString(inv)).Append('-').Append(p.Indice.ToString(inv)).Append(' ').Append(prefab);
                foreach(var c in new[]{v.x,v.y,v.z,pose.eulerAngles.y,sx})desc.Append(' ').Append(c.ToString("F2",inv));
            }
            Empreinte=Hacher(desc.ToString());
            string ligne="Enceinte : "+etape.ToString().ToLowerInvariant()+" · "+tours.ToString(inv)+" tour(s), "+pans.ToString(inv)+" pan(s), "+nbPortes.ToString(inv)+" porte(s).";
            return Refus.Count==0?ligne:ligne+"\n"+string.Join("\n",Refus);
        }

        static string Hacher(string texte)
        {
            using var sha=SHA256.Create();
            return string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(texte)).Select(b=>b.ToString("x2")));
        }
    }
}
