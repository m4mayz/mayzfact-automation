import {loadFont} from '@remotion/google-fonts/Anton';
import {loadFont as loadMontserrat} from '@remotion/google-fonts/Montserrat';

// Anton: huruf kapital tebal kondensed, paling mirip caption + angka di source i2xag.
export const {fontFamily: ANTON} = loadFont('normal', {weights: ['400'], subsets: ['latin']});
// Montserrat ExtraBold: tulisan tombol SUBSCRIBE/SUBSCRIBED (huruf lebar tebal kayak di source).
export const {fontFamily: MONTSERRAT} = loadMontserrat('normal', {weights: ['800'], subsets: ['latin']});
