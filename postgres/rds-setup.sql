CREATE TABLE public.title_basics (
	tconst varchar(999) NULL,
	titletype varchar(999) NULL,
	primarytitle varchar(999) NULL,
	originaltitle varchar(999) NULL,
	isadult varchar(999) NULL,
	startyear varchar(999) NULL,
	endyear varchar(999) NULL,
	runtimeminutes varchar(999) NULL,
	genres varchar(999) NULL
);

COPY public.title_basics FROM 'title.basics.tsv'  DELIMITER E'\t';