// Une figurine posée sur la carte : un bourg, une armée. Sa couleur est par sommet ; un sommet d'alpha 1 est une
// part teintée, qui prend la teinte du matériau (les toits d'un bourg à la couleur de son maître, l'étoffe d'une
// armée à celle de son pays). Comme le terrain, la figurine est mate : rien de la scène ne l'éclaire, ses faces sont
// ombrées d'une lumière fixe du nord-ouest, la même que celle du relief — un peu chaude au soleil, un peu froide à
// l'ombre —, et jamais plus sombres que `_Ombre`.
// Elle se dessine après le terrain et les noms des pays imprimés sur lui, et passe devant eux.
Shader "Forge/FormeDeCarte"
{
    Properties
    {
        [MainColor] _Teinte("Teinte des parts teintées", Color) = (0.6, 0.3, 0.2, 1)
        _Ombre("Part de lumière d'une face à l'ombre", Range(0, 1)) = 0.5
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Color.hlsl"
        CBUFFER_START(UnityPerMaterial)
            float4 _Teinte; float _Ombre;
        CBUFFER_END
        struct A { float3 p : POSITION; float3 n : NORMAL; float4 c : COLOR; };
        struct V { float4 clip : SV_POSITION; float3 n : TEXCOORD0; float4 c : COLOR; };
        V Vert(A a) { V o; o.clip = TransformObjectToHClip(a.p); o.n = TransformObjectToWorldNormal(a.n); o.c = a.c; return o; }
        ENDHLSL
        Pass
        {
            Name "Forme" Tags { "LightMode" = "UniversalForward" }
            Cull Off
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            static const float3 LUMIERE = float3(-0.5145, 0.686, 0.5145); // du nord-ouest, à mi-hauteur, comme sur le relief
            static const float3 CHAUDE = float3(1.05, 1.0, 0.93), FROIDE = float3(0.9, 0.95, 1.05);
            half4 Frag(V i) : SV_Target
            {
                // La couleur d'un sommet est écrite comme à l'écran ; celle du matériau arrive déjà dans l'espace du rendu.
                float3 propre = i.c.rgb;
                #ifndef UNITY_COLORSPACE_GAMMA
                propre = SRGBToLinear(propre);
                #endif
                float3 couleur = lerp(propre, _Teinte.rgb, step(0.5, i.c.a));
                float eclat = saturate(dot(normalize(i.n), LUMIERE) * 0.9 + 0.35);
                return half4(couleur * lerp(_Ombre, 1.0, eclat) * lerp(FROIDE, CHAUDE, eclat), 1.0);
            }
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly" Tags { "LightMode" = "DepthOnly" }
            Cull Off ZWrite On ColorMask R
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Profondeur
            half Profondeur(V i) : SV_Target { return i.clip.z; }
            ENDHLSL
        }
    }
}
