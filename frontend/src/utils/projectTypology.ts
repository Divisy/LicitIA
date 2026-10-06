export const TYPOLOGY_LABELS: Record<string, string> = {
  construccion: 'Construcción',
  edificacion: 'Edificación',
  vias: 'Vías',
  geotecnica: 'Geotécnica',
  espacio_publico: 'Espacio público',
  bicicarril: 'Bicicarril',
  senalizacion: 'Señalización',
  acueducto_alcantarillado: 'Acueducto y alcantarillado',
  parques: 'Parques',
  puentes: 'Puentes',
  otro: 'Otra',
}

export function typologyLabel(value: string): string {
  return TYPOLOGY_LABELS[value] || value
}
