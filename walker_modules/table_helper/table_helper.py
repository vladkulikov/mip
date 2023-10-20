import pandas as pd

class TableWriter:

    def __init__(self, file_name, mode = 'w', header = True, ind = False):
	
        self.mode = mode
        self.file_name = file_name
        self.header = header
        self.ind = ind

    def _pandas_to_table(self, df):

        if isinstance(df, list):
            df = pd.concat(df, axis = 1)
        if self.file_name.__contains__('csv'):
            df.to_csv(self.file_name, header = self.header, index = self.ind, sep = ';')
        if self.file_name.__contains__('xls'):
            with pd.ExcelWriter(self.file_name) as writer:
                df.to_excel(writer, header = self.header, index = self.ind)
		
    def _array_to_table(self, writeset, columns):

        if self.mode == 'a':
            df = TableReader(self.file_name)._table_to_pandas()
        else:
            df = pd.DataFrame()
        for i in range(len(writeset)):
            df[columns[i]] = writeset[i]
        self._pandas_to_table(df)
		
    def _row_to_table(self, writeset):

        if self.mode == 'a':
            df = TableReader(self.file_name)._table_to_pandas()
            rows = []
            for i in writeset:
                rows.append(i)
            dnew = pd.DataFrame(rows, columns = df.columns)
            df = df.append(dnew)
        else:
            df = pd.DataFrame(writeset)
        self._pandas_to_table(df)
			
class TableReader:

    def __init__(self, file_name, header = 0):
	
        self.file_name = file_name
        self.header = header
		
    def _table_to_pandas(self, columns = None):

        if self.file_name.__contains__('csv'):
            df = pd.read_csv(self.file_name, header = self.header, sep = ';', usecols = columns)
        if self.file_name.__contains__('xls'):
            df = pd.read_excel(self.file_name, header = self.header, usecols = columns)
        return df
			
    def _table_to_numpy(self, column):
	
        usecols = []
        usecols.append(column)
        df = self._table_to_pandas(usecols)
        return df[df.columns[0]].to_numpy()
			
    def _table_to_list(self, column):
	
        usecols = []
        usecols.append(column)
        df = self._table_to_pandas(usecols)
        return list(df[df.columns[0]])

    def _table_to_tuple(self, row):
	
        df = self._table_to_pandas()
        if row == -1:
            return tuple(df.tail(1))
        else:
            return tuple(df.loc[row])
		
    def _table_to_dictrow(self, row):
	
        df = self._table_to_pandas()
        if row == -1:
            return df.tail(1).iloc[0].to_dict()
        return df.loc[row].to_dict()
