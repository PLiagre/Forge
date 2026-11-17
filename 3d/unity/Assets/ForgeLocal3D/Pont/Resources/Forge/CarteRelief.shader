// Le terrain de la carte, d'un seul tenant. La teinte de chaque cellule se lit dans la palette par le numéro de son
// texel ; entre quatre texels voisins, la cellule qui pèse le plus l'emporte, d'autant plus net que l'on regarde de
// près : un bord de cellule reste un trait lisse, jamais un escalier. Le relief ombre la terre d'une lumière fixe du
// nord-ouest et pâlit les cimes ; la mer s'éclaircit vers le rivage et rend au large la couleur exacte de `_Mer`,
// celle du fond de la caméra. Rien n'est éclairé par la scène : la carte est mate.
Shader "Forge/CarteRelief"
{
    Properties
    {
        [NoScaleOffset] _Cellules("Cellules", 2D) = "black" {}
        [NoScaleOffset] _Palette("Palette", 2D) = "black" {}
        [NoScaleOffset] _Relief("Relief", 2D) = "black" {}
        _Mer("Mer au large", Color) = (0.08, 0.16, 0.3, 1)
        _Rivage("Mer au rivage", Color) = (0.2, 0.3, 0.42, 1)
        _Roche("Cimes", Color) = (0.85, 0.83, 0.78, 1)
        _PasDuRelief("Pas du relief, en km", Float) = 2
        _Fond("Fond de la mer, en km", Float) = 6
        _Plafond("Plus haute cime, en km", Float) = 40
        _Vigueur("Vigueur de l'ombre", Float) = 1.6
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            float4 _Cellules_TexelSize, _Palette_TexelSize, _Relief_TexelSize;
            float4 _Mer, _Rivage, _Roche; float _PasDuRelief, _Fond, _Plafond, _Vigueur;
        CBUFFER_END
        struct A { float3 p : POSITION; float2 uv : TEXCOORD0; };
        struct V { float4 clip : SV_POSITION; float2 uv : TEXCOORD0; };
        V Vert(A a) { V o; o.clip = TransformObjectToHClip(a.p); o.uv = a.uv; return o; }
        ENDHLSL
        Pass
        {
            Name "Carte" Tags { "LightMode" = "UniversalForward" }
            Cull Off
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            TEXTURE2D(_Cellules); TEXTURE2D(_Palette); TEXTURE2D(_Relief); SAMPLER(sampler_Relief);
            static const float3 LUMIERE = float3(-0.5145, 0.686, 0.5145); // du nord-ouest, à mi-hauteur
            float Altitude(float2 uv) { return SAMPLE_TEXTURE2D(_Relief, sampler_Relief, uv).r; }
            half4 Frag(V i) : SV_Target
            {
                // Les quatre texels de cellules autour du point, et le poids de chacun.
                float2 p = i.uv * _Cellules_TexelSize.zw - 0.5, base = floor(p), f = p - base;
                int2 dernier = int2(_Cellules_TexelSize.zw) - 1; int largeurPalette = (int)_Palette_TexelSize.z;
                float poids[4] = { (1 - f.x) * (1 - f.y), f.x * (1 - f.y), (1 - f.x) * f.y, f.x * f.y };
                float numero[4]; float4 teinte[4];
                for (int k = 0; k < 4; k++)
                {
                    int2 q = clamp(int2(base) + int2(k & 1, k >> 1), int2(0, 0), dernier);
                    numero[k] = round(LOAD_TEXTURE2D(_Cellules, q).r * 65535.0);
                    int n = (int)numero[k];
                    teinte[k] = LOAD_TEXTURE2D(_Palette, int2(n % largeurPalette, n / largeurPalette));
                }
                // Chaque texel pèse du poids de tous ceux de sa cellule, durci selon la taille d'un texel à l'écran.
                float durete = clamp(1.5 / max(max(fwidth(p.x), fwidth(p.y)), 1e-4), 1.0, 32.0);
                float somme = 0, terre = 0; float3 pigment = 0;
                for (int a = 0; a < 4; a++)
                {
                    float cellule = 0;
                    for (int b = 0; b < 4; b++) cellule += poids[b] * (numero[b] == numero[a] ? 1.0 : 0.0);
                    float s = poids[a] * pow(max(cellule, 1e-5), durete - 1.0);
                    somme += s; terre += s * teinte[a].a; pigment += s * teinte[a].a * teinte[a].rgb;
                }
                pigment /= max(terre, 1e-6); terre /= max(somme, 1e-6);

                float h = Altitude(i.uv); float2 t = _Relief_TexelSize.xy;
                float2 pente = float2(Altitude(i.uv + float2(t.x, 0)) - Altitude(i.uv - float2(t.x, 0)), Altitude(i.uv + float2(0, t.y)) - Altitude(i.uv - float2(0, t.y))) / (2.0 * _PasDuRelief);
                float3 normale = normalize(float3(-pente.x * _Vigueur, 1.0, -pente.y * _Vigueur));
                float ombre = clamp(dot(normale, LUMIERE) / LUMIERE.y, 0.45, 1.3); // 1 à plat
                float cime = smoothstep(0.5 * _Plafond, 0.9 * _Plafond, h);
                float3 sol = lerp(pigment, _Roche.rgb, 0.4 * cime) * ombre;
                float3 mer = lerp(_Rivage.rgb, _Mer.rgb, saturate(-h / _Fond));
                return half4(lerp(mer, sol, terre), 1);
            }
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly" Tags { "LightMode" = "DepthOnly" }
            Cull Off ZWrite On ColorMask R
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Profondeur
            half Profondeur(V i) : SV_Target { return i.clip.z; }
            ENDHLSL
        }
    }
}
