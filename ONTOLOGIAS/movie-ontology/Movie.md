# Movie

## Metadata

- **Tipo:** `owl:Class`
- **Ontologia:** movie-ontology

## Descripcion

Cinematographic or audiovisual work

## Superclases

- [[Entity]]

## Subclases

- [[AnimatedFilm]]
- [[Documentary]]
- [[FeatureFilm]]
- [[ShortFilm]]

## Clases Equivalentes

- `dbo:Film`
- `schema:Movie`

## Propiedades donde es Dominio

- [[belongsToCluster]] -> [[MovieCluster]]
- [[hasActor]] -> [[Actor]]
- [[hasAgeRating]] -> [[AgeRatingCategory]]
- [[hasAverageRating]] -> `xsd:decimal`
- [[hasBackdropUrl]] -> `xsd:anyURI`
- [[hasBoxOffice]] -> `xsd:decimal`
- [[hasBudget]] -> `xsd:decimal`
- [[hasCertification]] -> [[Certification]]
- [[hasCinematographer]] -> [[Cinematographer]]
- [[hasComposer]] -> [[Composer]]
- [[hasContextualDescription]] -> `xsd:string`
- [[hasCountryOfOrigin]] -> [[CountryOfOrigin]]
- [[hasCulturalContext]] -> [[CulturalContext]]
- [[hasDirector]] -> [[Director]]
- [[hasDuration]] -> `xsd:duration`
- [[hasEditor]] -> [[Editor]]
- [[hasGenre]] -> [[Genre]]
- [[hasHistoricalPeriod]] -> [[HistoricalPeriod]]
- [[hasHistoricalPeriodValue]] -> `xsd:string`
- [[hasIMDbID]] -> `xsd:string`
- [[hasIMDbRating]] -> `xsd:decimal`
- [[hasIMDbVoteCount]] -> `xsd:integer`
- [[hasKeyword]] -> [[Keyword]]
- [[hasLanguage]] -> [[Language]]
- [[hasMainGenre]] -> [[MainGenre]]
- [[hasMetascore]] -> `xsd:integer`
- [[hasMovieTypeValue]] -> `xsd:string`
- [[hasNarrativeElement]] -> [[NarrativeElement]]
- [[hasOriginalLanguage]] -> `xsd:string`
- [[hasOriginalTitle]] -> `xsd:string`
- [[hasPlotEmbedding]] -> `xsd:string`
- [[hasPlotStructure]] -> [[PlotStructure]]
- [[hasPlotStructureValue]] -> `xsd:string`
- [[hasPlotSummary]] -> `xsd:string`
- [[hasPopularity]] -> `xsd:decimal`
- [[hasPosterUrl]] -> `xsd:anyURI`
- [[hasProducer]] -> [[Producer]]
- [[hasProductionCompany]] -> [[ProductionCompany]]
- [[hasProductionCountries]] -> `xsd:string`
- [[hasRating]] -> [[Rating]]
- [[hasRatingCount]] -> `xsd:integer`
- [[hasScreenwriter]] -> [[Screenwriter]]
- [[hasSemanticTags]] -> `xsd:string`
- [[hasSimilarityScore]] -> `xsd:decimal`
- [[hasSpokenLanguages]] -> `xsd:string`
- [[hasSubgenre]] -> [[Subgenre]]
- [[hasTMDbID]] -> `xsd:string`
- [[hasTMDbRating]] -> `xsd:decimal`
- [[hasTMDbVoteCount]] -> `xsd:integer`
- [[hasTagline]] -> `xsd:string`
- [[hasTheme]] -> [[Theme]]
- [[hasThemeValue]] -> `xsd:string`
- [[hasTitle]] -> `xsd:string`
- [[hasTone]] -> [[Tone]]
- [[hasToneValue]] -> `xsd:string`
- [[hasVoteCount]] -> `xsd:integer`
- [[isSimilarTo]] -> [[Movie]]
- [[recommendedForCompanionType]] -> -
- [[releaseDate]] -> `xsd:date`
- [[runtime]] -> `xsd:integer`
- [[similarityMethod]] -> `xsd:string`
- [[suitableForMood]] -> -
- [[suitableForViewingContext]] -> -

## Propiedades donde es Rango

- [[containsMovie]] <- [[MovieCluster]]
- [[inMovie]] <- [[Role]]
- [[isActorIn]] <- [[Actor]]
- [[isCountryOfOriginOf]] <- [[CountryOfOrigin]]
- [[isDirectorOf]] <- [[Director]]
- [[isGenreOf]] <- [[Genre]]
- [[isKeywordOf]] <- [[Keyword]]
- [[isLanguageOf]] <- [[Language]]
- [[isSimilarTo]] <- [[Movie]]
- [[producedMovie]] <- [[ProductionCompany]]
