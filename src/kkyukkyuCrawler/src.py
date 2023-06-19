from __future__ import annotations
from typing import *
import re
import os
from timeit import default_timer as timer
from time import sleep
import ssl
from urllib.request import urlopen
from urllib.parse import quote
from urllib.error import HTTPError
from PyPDF2 import PdfReader
from tqdm import tqdm
from bs4 import BeautifulSoup, Tag, ResultSet


class Case:
    """
    Container class for case data.
    """

    """
    PRIVATE INSTANCE PARAMS
        - _id: Case ID (e.g. 1234다12345)
        - _ref_pg_no: The position (page #) where the case ID appears
        - _title: Case title (e.g. 대법원 2023. 6. 29. 선고 1234다12345 판결)
        - _issues: 판시/결정사항
        - _summaries: 판결/결정요지
        - _results: 주문
        - _claims: 청구/항소/반소 등 취지
        - _reasons: 이유
        - _src: The URL used for the GET request to obtain case data
    """
    _id: str
    _ref_pg_no: List[int]
    _title: Optional[str]
    _issues: Optional[List[str]]
    _summaries: Optional[List[str]]
    _results: Optional[List[str]]
    _claims: Optional[List[str]]
    _reasons: Optional[List[str]]
    _src: Optional[str]

    def __init__(self, _id: str, ref_pg_no: int):
        """
        Constructor.
        All properties except for _id and ref_pg_no are initialized as None.

        :param _id: Case ID
        :type _id: str
        :param ref_pg_no: The position (page #) where the case ID appears
        :type ref_pg_no: int
        """
        self._id = _id
        self._ref_pg_no = [ref_pg_no]
        self._title = None
        self._issues = None
        self._summaries = None
        self._results = None
        self._claims = None
        self._reasons = None
        self._src = None

    def __str__(self) -> str:  # for debugging
        if self._title is None:
            return str(None)
        buf: str = f'@title: {self.title}\n'
        if self._issues is not None:
            buf += '@issues\n  ' + '\n  '.join(self._issues) + '\n'
        if self._summaries is not None:
            buf += '@summaries\n  ' + '\n  '.join(self._summaries) + '\n'
        buf += '@results\n  ' + '\n  '.join(self._results) + '\n'
        if self._claims is not None:
            buf += '@claims\n  ' + '\n  '.join(self._claims) + '\n'
        buf += '@reasons\n  ' + '\n  '.join(self._reasons) + '\n'
        buf += f'@src: {self._src}'
        return buf

    """
    GETTERS
    """

    @property
    def id(self) -> str:
        return self._id

    @property
    def ref_pg_no(self) -> List[int]:
        return self._ref_pg_no

    @property
    def title(self) -> Optional[str]:
        return self._title

    @property
    def issues(self) -> Optional[List[str]]:
        return self._issues

    @property
    def summaries(self) -> Optional[List[str]]:
        return self._summaries

    @property
    def results(self) -> Optional[List[str]]:
        return self._results

    @property
    def claims(self) -> Optional[List[str]]:
        return self._claims

    @property
    def reasons(self) -> Optional[List[str]]:
        return self._reasons

    @property
    def src(self) -> Optional[str]:
        return self._src

    """
    SETTERS
    """

    def add_ref_pg_no(self, pg_no: int) -> None:
        self._ref_pg_no.append(pg_no)

    @title.setter
    def title(self, t: str) -> None:
        self._title = t

    @issues.setter
    def issues(self, t: List[str]) -> None:
        self._issues = t

    @summaries.setter
    def summaries(self, t: List[str]) -> None:
        self._summaries = t

    @results.setter
    def results(self, t: List[str]) -> None:
        self._results = t

    @claims.setter
    def claims(self, t: List[str]) -> None:
        self._claims = t

    @reasons.setter
    def reasons(self, t: List[str]) -> None:
        self._reasons = t

    @src.setter
    def src(self, t: str) -> None:
        self._src = t


@final
class Extractor:
    """
    A toolbox class for extracting case IDs, parsing HTML, and exporting.
    """

    """
    PRIVATE CLASS PARAMS (all constants)
        - _REGEX: Regex for extracting case IDs
        - _REQ_URL: The URL for the initial GET request
        - _REQ_URL2: The URL for the secondary(fall-back) GET request
        - _SEARCH_INT: The time interval between GET requests (0.5s)
        - _SLEEP_INT: The time duration to pause requests when a 429 error occurs (20s)
    """
    _REGEX: Final[str] = r'\d{2}(?:\d{2})?\s?[가-졓,족-힣]{1,2}\s?\d+'
    _REQ_URL: Final[str] = 'https://casenote.kr/search/?q='
    _REQ_URL2: Final[str] = 'https://casenote.kr/'
    _SEARCH_INT: Final[float] = 0.5
    _SLEEP_INT: Final[int] = 20

    """
    PUBLIC CLASS METHODS
        - extract_id: Extracting case IDs from PDF.
        - search: Perform a GET request to CASENOTE using the case ID, and parse the HTML response.
        - export: Export the Case objects with parsed case data to a txt file.
    """

    @classmethod
    def extract_id(cls, path: str, verbose: bool = False) -> List[Case]:
        """
        Extracting case IDs from PDF.

        The PDF should be unencrypted and in text format. The logic for OCR-based reading of PDFs in image format is
        currently not implemented.

        Please note that due to limitations in PDF parsing, the extraction of case IDs may not be perfect. There can be
        instances where case IDs are incorrectly extracted, strings other than case IDs are extracted, or some case IDs
        may not be extracted at all.
        During the testing process, it has been observed that the extraction of case IDs is incomplete in certain
        scenarios, such as when (1) a case ID spans multiple pgs (e.g., 1234다(pg break)12345), or (2) when there
        are immediate annotations following the case ID (e.g., 1234다12345(footnote)1)). In such cases, the extraction
        of case IDs may be limited.

        Furthermore, it should not be relied upon the consistent order of case ID extraction within the same pg. The
        order of extraction may vary and should not be trusted.

        :param str path: The path of the PDF to be read. Both absolute and relative paths are supported
        :type path: str
        :param bool verbose: If True, provide detailed report of the ID extraction process to stdout (default: False)
        :type verbose: bool

        :return: A list of Case objs generated from the extracted case IDs
        :rtype: list of Case
        """
        if verbose:
            Printer.title('extracting case ids')
            start: float = timer()

        # Load PDF
        reader: PdfReader = PdfReader(path)
        cases: List[Case] = []
        if verbose:
            Printer.report_w_annot('PDF loading', 'done')

        # Extract case IDs
        if verbose:
            Printer.report('extracting ids')
        else:
            pbar: tqdm = tqdm(desc='Extracting case ids', total=len(reader.pages), unit='pg', ncols=100)

        for pg_no, pg in enumerate(reader.pages):
            txt: str = ''.join(pg.extract_text())
            curr_pg_ids: List[str] = re.findall(cls._REGEX, txt)
            # If the found ID is newly discovered, add it; otherwise, update only the pg no
            for i, _id in enumerate(curr_pg_ids):
                curr_pg_ids[i] = re.sub(r'\s', '', _id)
                _id = curr_pg_ids[i]
                j: int = 0
                while j < len(cases):
                    if cases[j].id == _id:
                        if cases[j].ref_pg_no[-1] == pg_no:
                            break
                        else:
                            cases[j].add_ref_pg_no(pg_no)
                            break
                    j += 1
                if j == len(cases):
                    cases.append(Case(_id, pg_no))
            if verbose:
                if len(curr_pg_ids) == 0:
                    Printer.report_w_desc(f'page {pg_no + 1}', 'not found', 1)
                elif len(curr_pg_ids) > 4:
                    Printer.report_w_desc(f'page {pg_no + 1}', ', '.join(curr_pg_ids[:4]) + '...', 1)
                else:
                    Printer.report_w_desc(f'page {pg_no + 1}', ', '.join(curr_pg_ids), 1)
            else:
                pbar.update()

        # Report
        if verbose:
            Printer.report('returning list of Case objs')
            Printer.report_w_desc('read pages', str(len(reader.pages)), 1)
            Printer.report_w_desc('extracted cases', str(len(cases)), 1)
            Printer.report_w_desc('elapsed time', f'{round(1000 * (timer() - start), 2)}ms', 1)
        else:
            pbar.close()

        return cases

    @classmethod
    def search(cls, cases: List[Case], verbose: bool = False) -> None:
        """
        Perform a GET request to CASENOTE using the case ID, and parse the HTML response.

        It operates by filling in the properties of the given Case objects without any separate return.
        To ensure that the GET requests do not impose a burden on the CASENOTE server, they should be sent only once per
        0.5s. If a 429 error occurs, wait for 30 seconds before retrying. However, If the number of cases to search for
        is 10 or less, the GET requests will be made without intervals (i.e. fast mode).

        Since we are already sending requests only once per second, optimizing the HTML parsing logic may not provide
        significant benefits. It would be best to keep it as it is. The detailed parsing logic can be found in the
        PRIVATE CLASS METHOD section below.

        It is not using the 종합법률정보 API currently, because we don't want to go through the cumbersome approval process.

        :param cases: A list of Case objects containing the case IDs to be searched
        :type cases: list of Case
        :param verbose: If True, provide detailed report of the HTML parsing process to stdout (default: False)
        :type verbose: bool
        """
        if verbose:
            Printer.title('searching cases')
            start: float = timer()
            found: int = 0

        # Search
        if verbose:
            Printer.report('searching cases')
        else:
            pbar: tqdm = tqdm(desc='Searching cases', total=len(cases), unit='case', ncols=100)
        ssl._create_default_https_context = ssl._create_unverified_context
        fast_mode: bool = len(cases) <= 10
        i: int = 0
        while i < len(cases):
            try:
                # Get HTTP response
                soup, src = cls._get_http_res(cases[i].id)

                # When there are no search results
                if soup is None:
                    if verbose:
                        Printer.report_w_annot(f'case {cases[i].id}', '404 NOT FOUND', 1)
                    else:
                        pbar.update()

                    i += 1
                    if not fast_mode:
                        sleep(cls._SEARCH_INT)
                    continue

                # Parsing: title, issues, summaries, results, and reason; issues and summaries are optional
                cases[i].title = cls._parse_title(soup)
                cases[i].issues = cls._parse_issues(soup)
                cases[i].summaries = cls._parse_summaries(soup)
                cases[i].results = cls._parse_results(soup)
                cases[i].claims = cls._parse_claims(soup)
                cases[i].reasons = cls._parse_reasons(soup)
                cases[i].src = src

                if verbose:
                    found += 1
                    Printer.report_w_annot(f'case {cases[i].id}', '200 OK', 1)
                else:
                    pbar.update()

                i += 1
                if not fast_mode:
                    sleep(cls._SEARCH_INT)
            except HTTPError as e:
                # If the 429 error occurs, retry after _SLEEP_INT
                if e.code == 429:
                    if verbose:
                        Printer.report_w_annot(f'case {cases[i].id}', '429 TOO MANY REQ', 1)
                    sleep(cls._SLEEP_INT)
                else:
                    raise e

        # Report
        if verbose:
            m, n = len(cases), found
            Printer.report('returning list of Case objs')
            Printer.report_w_desc('searched cases', str(m), 1)
            Printer.report_w_desc('search succeeded', f'{n}({round(n / m * 100, 2)}%)', 1)
            Printer.report_w_desc('search failed', f'{m - n}({round((m - n) / m * 100, 2)}%)', 1)
            Printer.report_w_desc('elapsed time', f'{round(timer() - start, 2)}s', 1)
        else:
            pbar.close()

    @classmethod
    def export(cls, cases: List[Case], path: str, simple: bool = True, verbose: bool = False) -> None:
        """
        Export the Case objects with parsed case data to a txt file.

        If the case data cannot be found from CASENOTE, omit it and continue with the export.
        Currently, only the txt file format is supported for output.

        :param cases: A list of Case objects containing the case data to be exported.
        :type cases: list of Case
        :param path: The path of the PDF to be written. Both absolute and relative paths are supported. Please note that
                     if the file path already exists, it will be OVERWRITTEN
        :type path: str
        :param simple: If True, export only the issues and summaries. Otherwise, export all case data (default: True)
        :type simple: bool
        :param verbose: If True, provide detailed report of the exporting process to stdout (default: False)
        :type verbose: bool
        """
        if verbose:
            Printer.title('exporting search results')
            start: float = timer()
            cnt: int = 0

        # Export
        if verbose:
            Printer.report('exporting')
        else:
            pbar: tqdm = tqdm(desc='Exporting cases', total=len(cases), unit='case', ncols=100)
        f = open(path, 'w')

        for case in cases:
            if case.title is None:
                continue

            buf: str = f'{case.title}({", ".join(map(lambda x: str(x + 1), case.ref_pg_no))}면)\n'
            if case.issues is not None:
                buf += '[판시사항]\n  ' + '\n  '.join(case.issues) + '\n'
            elif simple:
                buf += '[판시사항] 없음\n'
            if case.summaries is not None:
                buf += '[판결요지]\n  ' + '\n  '.join(case.summaries) + '\n'
            elif simple:
                buf += '[판결요지] 없음\n'
            if not simple:
                buf += '[주문]\n  ' + '\n  '.join(case.results) + '\n'
                if case.claims is not None:
                    buf += '[청구취지]\n  ' + '\n  '.join(case.claims) + '\n'
                buf += '[이유]\n  ' + '\n  '.join(case.reasons) + '\n'
            buf += f'[출처] {case.src}\n\n'
            f.write(buf)

            if verbose:
                Printer.report_w_annot(f'case {case.id}', 'done', 1)
                cnt += 1
            else:
                pbar.update()

        f.close()
        if verbose:
            Printer.report('saving exported file')
            Printer.report_w_desc('path', os.path.abspath(path), 1)
            Printer.report_w_desc('exported cases', str(cnt), 1)
            Printer.report_w_desc('elapsed time', f'{round((timer() - start) * 1000, 2)}ms', 1)
        else:
            pbar.close()

    @classmethod
    def extract_and_export(cls, path_in: str, path_out: str, simple: bool = True, verbose: bool = False) -> None:
        """
        A thin wrapper that performs all the steps at once.

        :param path_in: The path of the PDF to be read. Both absolute and relative paths are supported
        :type path_in: str
        :param path_out: The path of the PDF to be written. Both absolute and relative paths are supported. Please note that
                         if the file path already exists, it will be OVERWRITTEN
        :type path_out: str
        :param simple: If True, export only the issues and summaries. Otherwise, export all case data (default: True)
        :type simple: bool
        :param verbose: If True, provide detailed report to stdout (default: False)
        :type verbose: bool
        """
        cases: List[Case] = cls.extract_id(path_in, verbose)
        cls.search(cases, verbose)
        cls.export(cases, path_out, simple, verbose)

    """
    PRIVATE CLASS METHODS
        - _get_http_res: Send a GET request to CASENOTE using the case ID and return the response and the URL used for 
                         the GET request.
        - _parse_title: Parse the title from the GET response.
        - _parse_issues: Parse issues from the GET response.
        - _parse_summaries: Parse summaries from the GET response.
        - _parse_results: Parse results from the GET response.
        - _parse_claims: Parse claims from the GET response.
        - _parse_reasons: Parse reasons from the GET response.
        - _prettify: Replace newline characters or consecutive spaces with a single space.

    PARSING LOGIC
    When sending a GET request to CASENOTE for case search, the response can be in one of the following HTML structures:
        (1) Directly routed to the pg displaying the full text of the case.
        (2) Directed to the pg displaying search results.
        (3) Directed to the pg indicating that no results were found.
    It is true that the exact conditions under which (1) or (2) responses are returned are not clear. However, it is 
    reasonable to speculate that (1) responses might be provided for well-known cases that are frequently searched for, 
    while (2) responses are likely for general search queries. The actual behavior may vary based on the CASENOTE 
    system's implementation and configuration.

    The HTML structure for each case is as follows:

    (1) pg displaying the full text of the case:
    <body> <div> <div> <div> <div> <div>
        <div class=cn-case-title> (판례제목; mandatory)
            <h1>case title</h1>
        </div>
        <div class=cn-case-body>
            <div> <div class=issue> (판시사항; optional)
                <p>issue1</p>
                <p>issue2</p>
                ...
            </div> </div>
            <div> <div class=summary> (판결요지; optional)
                <p>summary1</p>
                <p>summary2</p>
                ...
            </div> </div>
            <p>주문</p> (mandatory)
            <p>result1</p>
            <p>result2</p>
            ...
            <p>청구취지</p> (optional)
            <p>claim1</p>
            <p>claim2</p>
            <p>이유</p> (mandatory)
            <div class=reason>
                <p>이유1</p>
                <p>이유2</p>
                ...
            </div>
        </div>
    </div> </div> </div> </div> </div> </body>

    (2) pg displaying search results:
    <body> <div> <div class=cn-search-contents>
        <div class=searched-item>
            <div class=title>
                <a href=url1>search result1</a>
            </div>
        </div>
        <div class=searched-item>
            <div class=title>
                <a href=url2>search result2</a>
            </div>
        </div>
        ...
    </div> </div> </body>

    (3) pg indicating no results found:
    <body> <div> <div class=cn-search-contents>
        <p class=cn-search-empty>...</p>
    </div> </div> </body>

    Therefore, the parsing logic is structured as follows:
        1. The _get_http_res method accesses the 1st GET request URL and checks for the existence of the div with the 
        class 'cn-search-contents'. If it exists, it indicates the (1) case, so the corresponding response is returned. 
        If it doesn't exist, the method checks for the existence of the div with the class 'cn-search-empty'. If it 
        exists, it indicates the (3) case, and None is returned. If it doesn't exist, it indicates the (2) case. In this
        case, the method sequentially checks the divs with the class 'searched-item' to find the search result
        corresponding to the case ID. It then uses the href attribute of the 'a' tag to access the 2nd GET request URL
        and returns the response.
        2. If the _get_http_res method returns None, it means that there are no search results found, and parsing should
        be terminated. If a non-None value is returned, it indicates that the response is in the form of (1).
        3. The _parse_title method accesses the child tag h1 of the cn-case-title class div to parse the title.
        4. The _parse_issues method accesses the child p tags of the issue class div to parse the issues. Similarly, the
        _parse_summaries method accesses the child p tags of the summary class div to parse the summaries.
        5. The _parse_results method accesses the sibling p tags of <p>주문</p> to parse the results. Similarly, 
        _parse_claims method accesses the sibling p tags of <p>청구취지</p> to parse the claims.
        6. Lastly, the _parse_reasons method accesses the child p tags of the reason class div to parse the reasons.
    """

    @classmethod
    def _get_http_res(cls, _id: str) -> Tuple[Optional[BeautifulSoup], Optional[str]]:
        """
        Send a GET request to CASENOTE using the case ID and return the response and the URL used for the GET request.
        If necessary, it may involve an additional 2nd GET request.

        :param _id: The case ID to be used for the GET request
        :type _id: str

        :return: tuple of the BS object containing the response of the GET request, and the URL used for the request.
                 If there are no search results, then (None, None)
        :rtype: tuple of BeautifulSoup and str, both optional
        """
        html = urlopen(cls._REQ_URL + quote(_id))
        soup: BeautifulSoup = BeautifulSoup(html, 'html.parser')

        if soup.select_one('div.cn-search-contents'):
            # When there are no search results
            if soup.select_one('p.cn-search-empty') is not None:
                return None, None

            # Sequentially check the search results and retry the GET query
            # If there are no matching cases on the first pg of search results, terminate the search
            for it in soup.select('div.searched-item'):
                href = it.select_one('a')
                if href.text.find(_id) == -1:
                    continue
                html = urlopen(cls._REQ_URL2 + href['href'])
                soup = BeautifulSoup(html, 'html.parser')
                if soup.select_one('div.cn-case-title').text.find(_id) == -1:
                    return None, None
                return soup, cls._REQ_URL2 + href['href']
            return None, None
        else:
            # If redirected to the case pg, just verify the case id and return
            return soup, cls._REQ_URL + quote(_id)

    @classmethod
    def _parse_title(cls, soup: BeautifulSoup) -> str:
        """
        Parse the title from the GET response.

        :param soup: The BS object containing the response of the GET request
        :type soup: BeautifulSoup

        :return: The parsed title
        :rtype: str
        """
        title: str = soup.select_one('div.cn-case-title > h1').text.strip()
        trim_pos = title.find('[')
        assert trim_pos != -1
        return cls._prettify(title[:trim_pos - 1])

    @classmethod
    def _parse_issues(cls, soup: BeautifulSoup) -> Optional[List[str]]:
        """
        Parse issues from the GET response.

        :param soup: The BS object containing the response of the GET request
        :type soup: BeautifulSoup

        :return: The list of parsed issues. If there are no issues, then None
        :rtype: list of str, optional
        """
        issues: Optional[Tag] = soup.select_one('div.cn-case-body').select_one('div.issue')
        if issues is None:
            return None
        return [cls._prettify(issue.text) for issue in issues.select('p')]

    @classmethod
    def _parse_summaries(cls, soup: BeautifulSoup) -> Optional[List[str]]:
        """
        Parse summaries from the GET response.

        :param soup: The BS object containing the response of the GET request
        :type soup: BeautifulSoup

        :return: The list of parsed summaries. If there are no summaries, then None
        :rtype: list of str, optional
        """
        summaries: Optional[Tag] = soup.select_one('div.cn-case-body').select_one('div.summary')
        if summaries is None:
            return None
        return [cls._prettify(summary.text) for summary in summaries.select('p')]

    @classmethod
    def _parse_results(cls, soup: BeautifulSoup) -> List[str]:
        """
        Parse results from the GET response.

        :param soup: The BS object containing the response of the GET request
        :type soup: BeautifulSoup

        :return: The list of parsed results
        :rtype: list of str
        """
        results: List[str] = []
        cand: ResultSet = soup.select_one('div.cn-case-body').find_all('p', recursive=False)
        i: int = 0
        while i < len(cand):
            if re.sub(r'\s+', '', cand[i].text) == '주문':
                break
            i += 1
        assert i + 1 < len(cand)
        i += 1
        while i < len(cand):
            if cand[i]['class'][0] != 'main-sentence':
                break
            results.append(cls._prettify(cand[i].text))
            i += 1
        return results

    @classmethod
    def _parse_claims(cls, soup: BeautifulSoup) -> Optional[List[str]]:
        """
        Parse claims from the GET response.

        :param soup: The BS object containing the response of the GET request
        :type soup: BeautifulSoup

        :return: The list of parsed claims. If there are no claims, then None
        :rtype: list of str, optional
        """
        if soup.select_one('p.claim-title') is None:
            return None
        claims: List[str] = []
        cand: ResultSet = soup.select_one('div.cn-case-body').find_all('p', recursive=False)
        i: int = 0
        while i < len(cand):
            if cand[i]['class'][0] == 'claim-title':
                break
            i += 1
        assert i + 1 < len(cand)
        i += 1
        while i < len(cand):
            if cand[i]['class'][0] != 'main-sentence':
                break
            claims.append(cls._prettify(cand[i].text))
            i += 1
        return claims

    @classmethod
    def _parse_reasons(cls, soup: BeautifulSoup) -> List[str]:
        """
        Parse reasons from the GET response.

        :param soup: The BS object containing the response of the GET request
        :type soup: BeautifulSoup

        :return: The list of parsed reasons
        :rtype: list of str
        """
        reasons: Optional[Tag] = soup.select_one('div.cn-case-body').select_one('div.reason')
        reasons: List[str] = [cls._prettify(reason.text) for reason in reasons]
        return list(filter(lambda x: x != '', reasons))  # remove empty lines

    @classmethod
    def _prettify(cls, t: str) -> str:
        """
        Replace newline characters or consecutive spaces with a single space.

        :param t: The text to be prettified
        :type t: str

        :return: Prettified text
        :rtype: str
        """
        return re.sub(r'(\n|\s{2,})', ' ', t.strip())

    def __init__(self):
        raise Exception('Instantiation of this class is not allowed')


@final
class Printer:
    """
    Pretty-printer toolbox class. Nothing special.
    """

    """
    PRIVATE CLASS PARAMS (all constants)
        - _W: Width (60 words)
        - _TAB_SZ: Tab size (2 spaces)
    """
    _W: Final[int] = 60
    _TAB_SZ: Final[int] = 2

    """
    PUBLIC CLASS METHODS
        - title
        - report
        - report_w_annot
        - report_w_desc
    """

    @classmethod
    def title(cls, t: str) -> None:
        """
        Print title.
        e.g. ####################################
             ###             TITLE            ###
             ####################################

        :param t: Title to be printed out
        :type t: str
        """
        if len(t) > cls._W - 6:
            raise Exception('Too long')
        m: int = int((cls._W - len(t) - 6) / 2)
        n: int = cls._W - len(t) - 6 - m
        buf: str = '#' * cls._W + '\n'
        buf += '###' + ' ' * m + t.upper() + ' ' * n + '###\n'
        buf += '#' * cls._W
        print(buf)

    @classmethod
    def report(cls, t: str, tab_lv: int = 0) -> None:
        """
        Print a one-liner report.
        e.g. @step1

        :param t: Report to be printed out
        :type t: str
        :param tab_lv: Tab level (default: 0)
        :type tab_lv: int
        """
        buf: str = ' ' * cls._TAB_SZ * tab_lv + '@' + t
        print(buf)

    @classmethod
    def report_w_annot(cls, t: str, annotation: str, tab_lv: int = 0) -> None:
        """
        Print a one-liner report with annotation.
        e.g. @step1....................annotation

        :param t: Report to be printed out
        :type t: str
        :param annotation: Annotation to be printed out
        :type annotation: str
        :param tab_lv: Tab level (default: 0)
        :type tab_lv: int
        """
        n: int = cls._W - tab_lv * cls._TAB_SZ - 1 - len(t) - len(annotation)
        cls.report(t + '.' * n + annotation, tab_lv)

    @classmethod
    def report_w_desc(cls, t: str, desc: str, tab_lv: int = 0):
        """
        Print a one-liner report with annotation.
        e.g. @step1: description

        :param t: Report to be printed out
        :type t: str
        :param desc: Description to be printed out
        :type desc: str
        :param tab_lv: Tab level (default: 0)
        :type tab_lv: int
        """
        cls.report(t + ': ' + desc, tab_lv)

    def __init__(self):
        raise Exception('Instantiation of this class is not allowed')


"""
EXPORTS
"""
extract_id = Extractor.extract_id
search = Extractor.search
export = Extractor.export
extract_and_export = Extractor.extract_and_export
