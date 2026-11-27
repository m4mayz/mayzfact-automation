import {loadFont} from '@remotion/google-fonts/Anton';
import {loadFont as loadArimo} from '@remotion/google-fonts/Arimo';
import {loadFont as loadFredoka} from '@remotion/google-fonts/Fredoka';
import {loadFont as loadMontserrat} from '@remotion/google-fonts/Montserrat';

// Anton: huruf kapital tebal kondensed, paling mirip caption + angka di source i2xag.
export const {fontFamily: ANTON} = loadFont('normal', {weights: ['400'], subsets: ['latin']});
// Montserrat ExtraBold: tulisan tombol SUBSCRIBE/SUBSCRIBED (huruf lebar tebal kayak di source).
export const {fontFamily: MONTSERRAT} = loadMontserrat('normal', {weights: ['800'], subsets: ['latin']});
// Fredoka Bold: caption bulat dan ramah buat format FaktaCuil.
export const {fontFamily: FREDOKA} = loadFredoka('normal', {weights: ['600', '700'], subsets: ['latin']});
// Arimo Bold: padanan Arial Bold (font caption referensi TikTok) buat caption FaktaCuil "box"; ready dipakai sebelum ngukur lebar kata.
export const {fontFamily: ARIMO, waitUntilDone: arimoReady} = loadArimo('normal', {weights: ['700'], subsets: ['latin']});
