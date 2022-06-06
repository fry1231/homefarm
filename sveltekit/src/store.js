import { writable } from 'svelte/store';

export const incoming = writable({});
export const outgoing = writable({});
// {
//     board1: {
//         sensor1: data1,
//         ...
//     },
//     ...
// }
